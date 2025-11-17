from __future__ import annotations

"""
XCOM dispatcher — consolidated, edge-free, and chatty.

Public API stays `dispatch_notifications(...)` so existing callers
(`from backend.core.xcom_core import dispatch_notifications`) keep working.

Behavior (voice path):
  • Channel selection = explicit caller channels OR JSON monitor defaults.
  • Fire voice only when result['breach'] is True AND xcom_ready() is True.
  • No “rising edge” here. Cooldowns/creds are enforced downstream by
    xcom_ready()/dispatch_voice — we just show you what is gating.

Debug:
  • Loud "XCOM[...]" prints before/after every gate and on provider call.
"""

from typing import Any, Mapping, Sequence

from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log
from backend.data.data_locker import DataLocker

# consolidated stack
from backend.core.xcom_core.dispatch import dispatch_voice
from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.core.xcom_core.tts_service import TTSService
from backend.services.xcom_status_service import record_attempt
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


def _normalize_xcom_error_detail(msg: str | None) -> str:
    """Collapse noisy Twilio auth failures into a short, user-facing label."""

    if not msg:
        return ""

    text = str(msg)
    low = text.lower()

    if "twilio" in low and ("20003" in low or "authenticate" in low):
        return "twilio auth error"
    if "unable to create record" in low and "authenticate" in low:
        return "twilio auth error"

    return text


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
    source = ctx.get("source") or res.get("source") or "monitor"
    intent = res.get("intent") or f"{monitor_name}-breach"
    to_hint = ctx.get("to_number") or res.get("to_number")
    from_hint = ctx.get("from_number") or res.get("from_number")

    # DataLocker + consolidated config
    if db_path:
        dl = DataLocker.get_instance(str(db_path))
    else:
        dl = DataLocker.get_instance()
    cfg = XComConfigService(getattr(dl, "system", None), config=getattr(dl, "global_config", None))

    # Channel resolution
    chan = _as_channel_map(channels, cfg, monitor_name)
    provider_cfg = cfg.get_provider("api") or cfg.get_provider("twilio") or {}
    default_provider_name = str((provider_cfg or {}).get("provider") or "twilio")

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
        provider_name = default_provider_name
        provider_disabled = (provider_cfg is not None) and (provider_cfg.get("enabled", True) is False)

        if not breach:
            summary["channels"]["voice"] = {"ok": False, "skip": "breach-required"}
            record_attempt(
                dl,
                channel="voice",
                intent=intent,
                to_number=to_hint,
                from_number=from_hint,
                provider=provider_name,
                status="skipped",
                gated_by="breach-required",
                source=source,
            )
        elif not ok_ready:
            gate_reason = str(reason or "xcom-not-ready")
            summary["channels"]["voice"] = {"ok": False, "skip": gate_reason}
            record_attempt(
                dl,
                channel="voice",
                intent=intent,
                to_number=to_hint,
                from_number=from_hint,
                provider=provider_name,
                status="skipped",
                gated_by=gate_reason,
                source=source,
            )
        else:
            if provider_disabled:
                summary["channels"]["voice"] = {"ok": False, "skip": "provider-disabled"}
                record_attempt(
                    dl,
                    channel="voice",
                    intent=intent,
                    to_number=to_hint,
                    from_number=from_hint,
                    provider=provider_name,
                    status="skipped",
                    gated_by="provider-disabled",
                    source=source,
                )
            else:
                summary_text = (
                    res.get("summary")
                    or ctx.get("summary")
                    or body
                    or subject
                )
                message_text = res.get("message") or body or subject
                voice_event: dict[str, Any] = {
                    "monitor": monitor_name,
                    "breach": breach,
                    "summary": summary_text,
                    "message": message_text,
                    "subject": subject,
                    "body": body,
                    "source": source,
                }
                for key in ("label", "symbol", "value", "threshold"):
                    val = res.get(key)
                    if val is None:
                        val = ctx.get(key)
                    if val is not None:
                        voice_event[key] = val

                voice_ctx = dict(ctx)
                voice_ctx.setdefault("dl", dl)
                voice_profile_ctx = voice_ctx.get("voice")
                if isinstance(voice_profile_ctx, Mapping):
                    voice_profile_ctx = dict(voice_profile_ctx)
                else:
                    voice_profile_ctx = {}
                if isinstance(provider_cfg, Mapping):
                    voice_profile_ctx.setdefault("provider", provider_cfg)
                voice_ctx["voice"] = voice_profile_ctx

                try:
                    vr = dispatch_voice(voice_event, {"voice": True}, voice_ctx)
                    ok = bool(isinstance(vr, dict) and vr.get("ok"))
                    voice_payload: dict[str, Any] = {"ok": ok}
                    if isinstance(vr, dict):
                        for key in ("results", "error", "reason", "detail", "sid"):
                            if key in vr and vr[key] is not None:
                                voice_payload[key] = vr[key]

                    def _first_result_value(field: str) -> Any:
                        if isinstance(vr, dict):
                            results = vr.get("results")
                            if isinstance(results, list):
                                for item in results:
                                    if isinstance(item, Mapping) and item.get(field):
                                        return item.get(field)
                        return None

                    to_num = _first_result_value("to") or to_hint
                    from_num = _first_result_value("from") or from_hint
                    sid = _first_result_value("sid")
                    http_status = _first_result_value("http_status")

                    if not ok and voice_payload.get("error"):
                        summary["error"] = _normalize_xcom_error_detail(voice_payload.get("error"))

                    summary["channels"]["voice"] = voice_payload

                    if ok:
                        record_attempt(
                            dl,
                            channel="voice",
                            intent=intent,
                            to_number=to_num,
                            from_number=from_num,
                            provider=provider_name,
                            status="success",
                            sid=sid,
                            http_status=http_status,
                            source=source,
                        )
                    else:
                        err_msg = voice_payload.get("error") or voice_payload.get("reason") or "voice-dispatch-failed"
                        record_attempt(
                            dl,
                            channel="voice",
                            intent=intent,
                            to_number=to_num,
                            from_number=from_num,
                            provider=provider_name,
                            status="fail",
                            error_msg=err_msg,
                            source=source,
                        )
                except Exception as exc:
                    msg = str(exc)[:200]
                    detail = _normalize_xcom_error_detail(msg)
                    summary["error"] = detail or msg
                    summary["channels"]["voice"] = {
                        "ok": False,
                        "skip": "voice-dispatch-error",
                        "error": msg,
                    }
                    status_val = getattr(exc, "status", None)
                    record_attempt(
                        dl,
                        channel="voice",
                        intent=intent,
                        to_number=to_hint,
                        from_number=from_hint,
                        provider=provider_name,
                        status="fail",
                        error_msg=msg,
                        error_code=str(getattr(exc, "code", "")) or None,
                        http_status=int(status_val) if status_val is not None else None,
                        source=source,
                    )
    else:
        summary["channels"]["voice"] = {"ok": False, "skip": "disabled"}
        record_attempt(
            dl,
            channel="voice",
            intent=intent,
            to_number=to_hint,
            from_number=from_hint,
            provider=default_provider_name,
            status="skipped",
            gated_by="channel-disabled",
            source=source,
        )

    # ───────────── TTS (local pyttsx3) ─────────────
    if chan.get("tts", False):
        tts_text = None
        if ctx:
            tts_text = (
                (ctx.get("voice") or {}).get("tts")
                or ctx.get("tts")
                or ctx.get("body")
            )
        if not tts_text:
            tts_text = body

        tts_ok = False
        tts_error = None

        try:
            provider_cfg = cfg.get_provider("tts")
            voice_name = None
            speed = None
            if isinstance(provider_cfg, Mapping):
                voice_name = provider_cfg.get("voice") or provider_cfg.get("voice_name")
                raw_speed = provider_cfg.get("speed") or provider_cfg.get("rate")
                if isinstance(raw_speed, (int, float)):
                    speed = int(raw_speed)
                elif isinstance(raw_speed, str) and raw_speed.isdigit():
                    speed = int(raw_speed)
            elif isinstance(provider_cfg, str):
                voice_name = provider_cfg
            tts_svc = TTSService(voice_name, speed)
        except Exception as exc:  # pragma: no cover - instantiation errors
            tts_error = str(exc)
        else:
            recipient = ctx.get("recipient") or to_hint or monitor_name
            try:
                tts_ok = bool(tts_svc.send(recipient or "local", tts_text, dl=dl))
            except Exception as exc:  # pragma: no cover - pyttsx3 failures
                tts_error = str(exc)

        if tts_ok:
            summary["channels"]["tts"] = {"ok": True}
        else:
            summary["channels"]["tts"] = {"ok": False, "error": tts_error or "tts failed"}
    else:
        summary["channels"]["tts"] = {"ok": False, "skip": "disabled"}

    # SMS placeholder (still disabled unless wired later)
    for k in ("sms",):
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

    return summary
