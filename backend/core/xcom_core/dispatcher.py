from __future__ import annotations

"""
XCOM dispatcher — consolidated, edge-free, and chatty.

Public API stays `dispatch_notifications(...)` so existing callers
(`from backend.core.xcom_core import dispatch_notifications`) keep working.

Behavior (voice path):
  • Channel selection = explicit caller channels OR JSON monitor defaults.
  • Fire voice only when result['breach'] is True AND xcom_ready() is True.
  • No “rising edge” here. Cooldowns/creds are enforced downstream by
    xcom_ready()/VoiceService — we just show you what is gating.

Debug:
  • Loud "XCOM[...]" prints before/after every gate and on provider call.
"""

from typing import Any, Mapping, Sequence

from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log
from backend.data.data_locker import DataLocker

# consolidated stack
from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.core.xcom_core.voice_service import VoiceService
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_ready


# ---------- helpers ----------

def _normalize_channels(ch: Mapping[str, Any] | Sequence[str] | str | None) -> list[str]:
    if ch is None:
        return []
    if isinstance(ch, Mapping):
        return [name for name, enabled in ch.items() if enabled]
    if isinstance(ch, str):
        ch = ch.split(",")
    return [str(name).strip().lower() for name in ch if str(name).strip()]


def _as_channel_map(
    ch: Mapping[str, Any] | Sequence[str] | str | None,
    cfg: XComConfigService,
    monitor_name: str,
) -> dict[str, bool]:
    """
    Merge explicit caller choice with JSON monitor defaults.
    We ALWAYS prefer monitor-level notifications to avoid the global
    'channels.voice' accidentally gating things.
    """
    explicit: dict[str, bool] | None = None
    if isinstance(ch, Mapping):
        explicit = {k: bool(v) for k, v in ch.items()}

    if explicit is None:
        names = set(_normalize_channels(ch))
        explicit = {
            "voice": "voice" in names,
            "system": "system" in names,
            "sms": "sms" in names,
            "tts": "tts" in names,
        }

    # If caller didn’t request anything explicitly, use JSON monitor defaults.
    if not any(explicit.values()):
        # channels_for(monitor) already prioritizes monitor.notifications.*
        # over any global channels.* block.
        explicit = {**cfg.channels_for(monitor_name)}  # copy

    for k in ("voice", "system", "sms", "tts"):
        explicit.setdefault(k, False)
    return explicit


def _safe_str(v: Any, maxlen: int = 120) -> str:
    s = "" if v is None else str(v)
    return s if len(s) <= maxlen else (s[: maxlen - 1] + "…")


# ---------- public API ----------

def dispatch_notifications(
    *,
    monitor_name: str,
    result: Mapping[str, Any] | None = None,
    channels: Mapping[str, Any] | Sequence[str] | str | None = None,
    context: Mapping[str, Any] | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Single entrypoint used by monitors/tests/console.

    Returns:
      {
        "monitor": "...",
        "breach": bool,
        "channels": { "voice": {...}, "system": {...}, "sms": {...}, "tts": {...} },
        "success": bool,
        "context": {...}, "result": {...}
      }
    """
    # Inputs
    ctx = dict(context or {})
    res = dict(result or {})
    subject = ctx.get("subject") or f"[{monitor_name}] alert"
    body = ctx.get("body") or res.get("message") or res.get("summary") or ""
    breach = bool(res.get("breach", False))

    # DataLocker + consolidated config
    if db_path:
        dl = DataLocker.get_instance(str(db_path))
    else:
        dl = DataLocker.get_instance()
    cfg = XComConfigService(getattr(dl, "system", None), config=getattr(dl, "global_config", None))

    # Channel resolution
    chan = _as_channel_map(channels, cfg, monitor_name)

    print(f"XCOM[ENTRY] monitor={monitor_name} breach={breach} "
          f"caller_channels={_normalize_channels(channels) if channels else '—'}")
    print(f"XCOM[CHAN]  resolved={chan}")

    summary: dict[str, Any] = {
        "monitor": monitor_name,
        "breach": breach,
        "channels": {},
        "context": {"subject": subject, "body": _safe_str(body)},
        "result": res,
    }

    # “System” is just a flag for UI/console
    summary["channels"]["system"] = {"ok": bool(chan.get("system", False))}

    # Voice path — no “rising edge” here; let readiness/cooldown/creds gate.
    if chan.get("voice", False):
        ok_ready, reason = xcom_ready(dl, cfg=getattr(dl, "global_config", None))
        print(f"XCOM[GATE] breach={breach} ready={ok_ready} reason={reason}")

        if not breach:
            summary["channels"]["voice"] = {"ok": False, "skip": "breach-required"}
            print("XCOM[VOICE] skip: breach-required")
        elif not ok_ready:
            summary["channels"]["voice"] = {"ok": False, "skip": str(reason or "xcom-not-ready")}
            print(f"XCOM[VOICE] skip: not-ready → {reason}")
        else:
            # choose provider (prefer “api” if present, else “twilio”)
            provider_cfg = cfg.get_provider("api") or cfg.get_provider("twilio") or {}
            provider_disabled = (provider_cfg is not None) and (provider_cfg.get("enabled", True) is False)
            print(f"XCOM[PROV] type={'api' if cfg.get_provider('api') else 'twilio' if cfg.get_provider('twilio') else '∅'} "
                  f"disabled={provider_disabled}")

            if provider_disabled:
                summary["channels"]["voice"] = {"ok": False, "skip": "provider-disabled"}
                print("XCOM[VOICE] skip: provider-disabled")
            else:
                try:
                    svc = VoiceService(provider_cfg)
                    ok, sid, to_num, from_num = svc.call(None, subject, body, dl=dl)
                    voice_payload = {"ok": bool(ok)}
                    if ok:
                        voice_payload.update({"sid": sid, "to": to_num, "from": from_num})
                        print(f"XCOM[VOICE] ✔ ok sid={sid} to={to_num} from={from_num}")
                    else:
                        print("XCOM[VOICE] ✖ call returned ok=False")
                    summary["channels"]["voice"] = voice_payload
                except Exception as exc:
                    msg = str(exc)[:200]
                    summary["channels"]["voice"] = {"ok": False, "skip": "twilio-error", "error": msg}
                    print(f"XCOM[VOICE] ✖ exception: {msg}")
    else:
        summary["channels"]["voice"] = {"ok": False, "skip": "disabled"}
        print("XCOM[VOICE] skip: channel.voice=False")

    # SMS/TTS placeholders (still disabled unless wired later)
    for k in ("sms", "tts"):
        if k not in summary["channels"]:
            summary["channels"][k] = {"ok": False, "skip": "disabled" if not chan.get(k, False) else "not-implemented"}

    # Overall success if any requested-and-permitted channel succeeded
    summary["success"] = any(v.get("ok") for name, v in summary["channels"].items() if chan.get(name, False))

    # structured log
    try:
        log.debug(
            "XCom dispatch",
            source="xcom.dispatcher",
            payload={
                "monitor": monitor_name,
                "breach": breach,
                "channels": {k: bool(chan.get(k)) for k in ("voice", "system", "sms", "tts")},
                "success": summary["success"],
            },
        )
    except Exception:
        pass

    print(f"XCOM[EXIT] success={summary['success']} channels={summary['channels']}")
    return summary
