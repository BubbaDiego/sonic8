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
from backend.core.xcom_core.voice_service import VoiceService, place_call
from backend.services.xcom_status_service import record_attempt
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_ready

# We rely on the existing helper if available; otherwise we degrade gracefully
try:
    from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_live_status
except Exception:
    def xcom_live_status(dl: Any, cfg: dict | None = None) -> tuple[bool, str]:
        val = getattr(dl, "xcom_live", None)
        if isinstance(val, bool):
            return val, "RUNTIME"
        return True, "RUNTIME"


__all__ = ["dispatch_notifications", "dispatch_voice_if_needed"]


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
    source = ctx.get("source") or res.get("source") or "monitor"
    intent = res.get("intent") or f"{monitor_name}-breach"
    to_hint = ctx.get("to_number") or res.get("to_number")
    from_hint = ctx.get("from_number") or res.get("from_number")

    # DataLocker + consolidated config view
    if db_path:
        dl = DataLocker.get_instance(str(db_path))
    else:
        dl = DataLocker.get_instance()

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
            record_attempt(
                dl,
                channel="voice",
                intent=intent,
                to_number=to_hint,
                from_number=from_hint,
                provider="twilio",
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
                provider="twilio",
                status="skipped",
                gated_by=gate_reason,
                source=source,
            )
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
                    record_attempt(
                        dl,
                        channel="voice",
                        intent=intent,
                        to_number=to_hint,
                        from_number=from_hint,
                        provider="twilio",
                        status="skipped",
                        gated_by="provider-disabled",
                        source=source,
                    )
                else:
                    svc = VoiceService(provider_cfg)
                    ok, sid, to_num, from_num, http_status = svc.call(None, subject, body, dl=dl)
                    payload: dict[str, Any] = {"ok": bool(ok)}
                    if ok:
                        if sid is not None:
                            payload["sid"] = sid
                        if to_num is not None:
                            payload["to"] = to_num
                        if from_num is not None:
                            payload["from"] = from_num
                        if http_status is not None:
                            payload["http_status"] = http_status
                        record_attempt(
                            dl,
                            channel="voice",
                            intent=intent,
                            to_number=to_num or to_hint,
                            from_number=from_num or from_hint,
                            provider="twilio",
                            status="success",
                            sid=sid,
                            http_status=http_status,
                            source=source,
                        )
                    else:
                        record_attempt(
                            dl,
                            channel="voice",
                            intent=intent,
                            to_number=to_num or to_hint,
                            from_number=from_num or from_hint,
                            provider="twilio",
                            status="fail",
                            error_msg="voice-service-returned-false",
                            source=source,
                        )
                    summary["channels"]["voice"] = payload
            except Exception as exc:  # don't crash dispatch — report reason
                msg = str(exc)[:160]
                summary["channels"]["voice"] = {
                    "ok": False,
                    "skip": "twilio-error",
                    "error": msg,
                }
                status_val = getattr(exc, "status", None)
                record_attempt(
                    dl,
                    channel="voice",
                    intent=intent,
                    to_number=to_hint,
                    from_number=from_hint,
                    provider="twilio",
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
            provider="twilio",
            status="skipped",
            gated_by="channel-disabled",
            source=source,
        )

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


# ---------- lightweight voice dispatcher for monitors ----------


def _resolve_cfg(dl: Any) -> dict:
    cfg = getattr(dl, "global_config", None)
    if isinstance(cfg, dict):
        return cfg
    try:
        from backend.core.reporting_core.sonic_reporting.config_probe import discover_json_path, parse_json

        path = discover_json_path(None)
        if path:
            obj, _err, _meta = parse_json(path)
            if isinstance(obj, dict):
                return obj
    except Exception:
        pass
    return {}


def _voice_enabled(cfg: dict, dl: Any) -> bool:
    v = cfg.get("liquid", {}).get("notifications", {}).get("voice")
    if isinstance(v, bool):
        return v
    rv = getattr(dl, "voice_enabled", None)
    if isinstance(rv, bool):
        return rv
    return True


def _is_snoozed(dl: Any) -> bool:
    for key in ("monitor_snoozed", "liquid_snoozed", "liquid_snooze"):
        v = getattr(dl, key, 0)
        try:
            return bool(v) and float(v) > 0
        except Exception:
            if isinstance(v, bool):
                return v
    return False


def _provider_cooldown_ok(dl: Any) -> bool:
    v = getattr(dl, "xcom_provider_cooldown_ok", None)
    if isinstance(v, bool):
        return v
    v = getattr(dl, "provider_cooldown_ok", None)
    if isinstance(v, bool):
        return v
    return True


def _compute_voice_gating(dl: Any, breach: bool, reason_ctx: dict) -> tuple[bool, str]:
    if not breach:
        return False, "no_breach"

    cfg = _resolve_cfg(dl)
    live, _src = xcom_live_status(dl, cfg=cfg)
    if not live:
        return False, "xcom_disabled"

    if not _voice_enabled(cfg, dl):
        return False, "voice_channel_disabled"

    if _is_snoozed(dl):
        return False, "snoozed"

    if not _provider_cooldown_ok(dl):
        return False, "provider_cooldown"

    return True, "ok"


try:
    from twilio.base.exceptions import TwilioException  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    class TwilioException(Exception):
        ...


def dispatch_voice_if_needed(
    dl: Any,
    *,
    breach: bool,
    to_number: str,
    from_number: str,
    reason_ctx: dict,
) -> bool:
    """
    Decide gates and, if allowed, place a Twilio call.
    Records an attempt for all outcomes.
    """

    can_call, gate_reason = _compute_voice_gating(dl, breach, reason_ctx)

    if not can_call:
        record_attempt(
            dl,
            channel="voice",
            intent=reason_ctx.get("intent", "liquid-breach"),
            to_number=to_number,
            from_number=from_number,
            provider="twilio",
            status="skipped",
            gated_by=gate_reason,
            source=reason_ctx.get("source", "monitor"),
        )
        return False

    try:
        sid, http_status = place_call(dl, to_number=to_number, from_number=from_number, ctx=reason_ctx)
        record_attempt(
            dl,
            channel="voice",
            intent=reason_ctx.get("intent", "liquid-breach"),
            to_number=to_number,
            from_number=from_number,
            provider="twilio",
            status="success",
            sid=sid,
            http_status=http_status,
            source=reason_ctx.get("source", "monitor"),
        )
        return True
    except TwilioException as e:
        code = getattr(e, "code", None)
        status = getattr(e, "status", None)
        record_attempt(
            dl,
            channel="voice",
            intent=reason_ctx.get("intent", "liquid-breach"),
            to_number=to_number,
            from_number=from_number,
            provider="twilio",
            status="fail",
            error_code=str(code) if code is not None else None,
            http_status=int(status) if status is not None else None,
            error_msg=str(e)[:240],
            source=reason_ctx.get("source", "monitor"),
        )
        return False
    except Exception as e:
        record_attempt(
            dl,
            channel="voice",
            intent=reason_ctx.get("intent", "liquid-breach"),
            to_number=to_number,
            from_number=from_number,
            provider="twilio",
            status="fail",
            error_msg=str(e)[:240],
            source=reason_ctx.get("source", "monitor"),
        )
        return False
