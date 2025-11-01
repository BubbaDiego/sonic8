"""
Consolidated XCOM dispatcher (no legacy).

Public API:
    dispatch_notifications(
        monitor_name=...,
        result={"breach": bool, "summary": "...", ...},
        channels=None | dict | list[str] | "csv",
        context={"subject": "...", "body": "...", ...},
        db_path=None,
    )

Behavior:
  • Channels are taken from explicit call or JSON defaults via XComConfigService.channels_for(monitor).
  • A voice call is attempted only when result['breach'] is True AND xcom_ready(...) gates are satisfied.
  • Blast radius is display-only (never gates dispatch).
  • If a per-monitor mapping exists (channels.<monitor> or <monitor>.notifications), the global channels.voice is ignored.
  • Logs resolved defaults and effective channels each call to ease diagnostics.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log
from backend.data.data_locker import DataLocker

from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.core.xcom_core.voice_service import VoiceService
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_ready


__all__ = ["dispatch_notifications"]


def _normalize_channels(channels: Mapping[str, Any] | Sequence[str] | str | None) -> list[str]:
    """
    Normalize caller channel selections to a list[str] of names.
    Accepts: None | {"voice": True, "system": False, ...} | ["voice", "system"] | "voice,system"
    """
    if channels is None:
        return []
    if isinstance(channels, Mapping):
        return [name for name, enabled in channels.items() if enabled]
    if isinstance(channels, str):
        channels = channels.split(",")
    return [str(name).strip().lower() for name in channels if str(name).strip()]


def _as_channel_map(
    channels: Mapping[str, Any] | Sequence[str] | str | None,
    cfg: XComConfigService,
    monitor_name: str,
) -> dict[str, bool]:
    """
    Merge explicit caller choices with JSON defaults (cfg.channels_for).
    Ensures keys for 'voice', 'system', 'sms', 'tts' are always present.
    """
    explicit: dict[str, bool] | None = None
    if isinstance(channels, Mapping):
        explicit = {k.lower(): bool(v) for k, v in channels.items()}

    if explicit is None:
        names = set(_normalize_channels(channels))
        explicit = {
            "voice": "voice" in names,
            "system": "system" in names,
            "sms": "sms" in names,
            "tts": "tts" in names,
        }

    # If caller gave nothing (all False), fall back to JSON-configured channels for this monitor
    if not any(explicit.values()):
        explicit = {**cfg.channels_for(monitor_name)}  # copy

    # Guarantee presence of known keys
    for k in ("voice", "system", "sms", "tts"):
        explicit.setdefault(k, False)

    return explicit


def _resolve_voice_provider(dl: DataLocker, cfg: XComConfigService) -> dict[str, Any]:
    """
    Prefer 'twilio' provider. If JSON returns {}, fall back to system var 'xcom_providers.twilio.enabled'.
    Default to enabled=True so STUB/lab runs aren't blocked.
    """
    # Prefer Twilio explicitly (we're doing voice calls)
    prov = cfg.get_provider("twilio")

    # If JSON has nothing, consult system var
    if not isinstance(prov, dict) or not prov:
        try:
            sysvars = getattr(dl, "system", None)
            xpv = (sysvars.get_var("xcom_providers") or {}) if sysvars else {}
            tw = xpv.get("twilio") or {}
            if isinstance(tw, dict) and "enabled" in tw:
                prov = {"enabled": bool(tw.get("enabled"))}
        except Exception:
            prov = prov or {}

    # If still nothing, assume enabled (VoiceService can still decide based on creds)
    if not isinstance(prov, dict) or not prov:
        prov = {"enabled": True}

    return prov


def dispatch_notifications(
    *,
    monitor_name: str,
    result: Mapping[str, Any] | None = None,
    channels: Mapping[str, Any] | Sequence[str] | str | None = None,
    context: Mapping[str, Any] | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Unified XCOM dispatcher used by monitors/console/tests.

    Returns a summary:
      {
        "monitor": "...",
        "breach": bool,
        "channels": {
          "voice": {"ok": bool, "sid": "...", "to": "...", "from": "..."} | {"ok": False, "skip": "..."},
          "system": {"ok": bool}, "sms": {...}, "tts": {...}
        },
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

    # DataLocker + consolidated config view
    dl = DataLocker.get_instance(str(db_path or MOTHER_DB_PATH))

    # IMPORTANT: Pass both system and the loaded JSON so per-monitor channels are honored.
    cfg = XComConfigService(getattr(dl, "system", None), config=getattr(dl, "global_config", None))

    # For diagnostics: show JSON-resolved defaults for the monitor
    resolved_defaults = cfg.channels_for(monitor_name)

    # Merge caller-provided channels with defaults
    chan = _as_channel_map(channels, cfg, monitor_name)

    # Log the channels we resolved (once per dispatch) to make any config mismatch obvious
    log.debug(
        "XCOM channels resolved",
        source="dispatch_notifications",
        payload={
            "monitor": monitor_name,
            "defaults": resolved_defaults,
            "effective": {k: bool(chan.get(k)) for k in ("voice", "system", "sms", "tts")},
        },
    )

    summary: dict[str, Any] = {
        "monitor": monitor_name,
        "breach": breach,
        "channels": {},
        "context": ctx,
        "result": res,
    }

    # System channel is display-only success (console/UI)
    summary["channels"]["system"] = {"ok": bool(chan.get("system", False))}

    # Voice channel — same guard as monitors (no blast gating)
    if chan.get("voice", False):
        ok_ready, reason = xcom_ready(dl, cfg=getattr(dl, "global_config", None))
        if not breach:
            summary["channels"]["voice"] = {"ok": False, "skip": "breach-required"}
        elif not ok_ready:
            summary["channels"]["voice"] = {"ok": False, "skip": str(reason or "xcom-not-ready")}
        else:
            try:
                provider_cfg = _resolve_voice_provider(dl, cfg)

                # Log the resolved provider gate (enabled flag) to kill ambiguity
                log.debug(
                    "XCOM voice provider resolved",
                    source="dispatch_notifications",
                    payload={"provider": provider_cfg},
                )

                if isinstance(provider_cfg, dict) and (provider_cfg.get("enabled", True) is False):
                    summary["channels"]["voice"] = {"ok": False, "skip": "provider-disabled"}
                else:
                    svc = VoiceService(provider_cfg)
                    ok, sid, to_num, from_num = svc.call(None, subject, body, dl=dl)
                    summary["channels"]["voice"] = {
                        "ok": bool(ok),
                        **({"sid": sid, "to": to_num, "from": from_num} if ok else {}),
                    }
            except Exception as exc:  # don't crash dispatch — report reason
                summary["channels"]["voice"] = {
                    "ok": False,
                    "skip": "twilio-error",
                    "error": str(exc)[:160],
                }
    else:
        summary["channels"]["voice"] = {"ok": False, "skip": "disabled"}

    # SMS/TTS placeholders — wire when providers enabled
    for k in ("sms", "tts"):
        if k not in summary["channels"]:
            summary["channels"][k] = {
                "ok": False,
                "skip": "disabled" if not chan.get(k, False) else "not-implemented"
            }

    # Overall success if any requested & permitted channel succeeded
    summary["success"] = any(
        v.get("ok") for name, v in summary["channels"].items() if chan.get(name, False)
    )

    log.debug(
        "XCom consolidated dispatch",
        source="dispatch_notifications",
        payload={
            "monitor": monitor_name,
            "breach": breach,
            "channels": {k: bool(chan.get(k)) for k in ("voice", "system", "sms", "tts")},
            "success": summary["success"],
        },
    )

    return summary
