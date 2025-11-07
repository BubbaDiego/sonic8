# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Optional

# Voice provider
from backend.core.xcom_core.voice_service import place_call

# Alerts DB (to persist attempts & last_dispatch_at)
from backend.data import dl_alerts

# In-memory panel telemetry (kept; coexist with DB attempts)
try:
    from backend.services.xcom_status_service import record_attempt as mem_record_attempt  # type: ignore
except Exception:
    def mem_record_attempt(*_a, **_k):  # type: ignore
        return None

# XCOM Live resolver for gating
try:
    from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_live_status
except Exception:
    def xcom_live_status(dl: Any, cfg: dict | None = None) -> tuple[bool, str]:
        v = getattr(dl, "xcom_live", None)
        return (bool(v), "RUNTIME") if isinstance(v, bool) else (True, "RUNTIME")

try:
    from twilio.base.exceptions import TwilioException  # type: ignore
except Exception:
    class TwilioException(Exception):  # type: ignore
        ...


def _resolve_cfg(dl: Any) -> dict:
    cfg = getattr(dl, "global_config", None)
    return cfg if isinstance(cfg, dict) else {}

def _voice_enabled(cfg: dict, dl: Any) -> bool:
    n = cfg.get("liquid", {}).get("notifications", {}) or {}
    if "voice" in n:
        return bool(n["voice"])
    v = getattr(dl, "voice_enabled", None)
    return bool(v) if isinstance(v, bool) else True

def _is_snoozed(dl: Any) -> bool:
    for key in ("monitor_snoozed", "liquid_snoozed", "liquid_snooze"):
        v = getattr(dl, key, 0)
        try:
            if float(v) > 0: return True
        except Exception:
            if isinstance(v, bool) and v: return True
    return False

def _provider_cooldown_ok(dl: Any) -> bool:
    for key in ("xcom_provider_cooldown_ok", "provider_cooldown_ok"):
        v = getattr(dl, key, None)
        if isinstance(v, bool): return v
    return True

def _compute_voice_gating(dl: Any, breach: bool, reason_ctx: dict) -> tuple[bool, str]:
    if not breach:
        return False, "no_breach"
    live, _src = xcom_live_status(dl, cfg=_resolve_cfg(dl))
    if not live:
        return False, "xcom_disabled"
    if not _voice_enabled(_resolve_cfg(dl), dl):
        return False, "voice_channel_disabled"
    if _is_snoozed(dl):
        return False, "snoozed"
    if not _provider_cooldown_ok(dl):
        return False, "provider_cooldown"
    return True, "ok"

def _ctx_alert_id(dl: Any, reason_ctx: dict) -> Optional[str]:
    aid = reason_ctx.get("alert_id")
    if isinstance(aid, str):
        return aid
    # Try to find one by monitor+symbol if provided
    mon = reason_ctx.get("source")  # we used "liquid"
    sym = reason_ctx.get("symbol")
    if isinstance(mon, str) and isinstance(sym, str):
        opens = dl_alerts.list_open(dl, kind="breach", monitor=mon)
        for a in opens:
            if a.get("symbol") == sym.upper():
                return a.get("id")
    return None

def dispatch_voice_if_needed(
    dl: Any,
    *,
    breach: bool,
    to_number: Optional[str],
    from_number: Optional[str],
    reason_ctx: dict
) -> bool:
    can_call, gate_reason = _compute_voice_gating(dl, breach, reason_ctx)
    alert_id = _ctx_alert_id(dl, reason_ctx)

    if not can_call:
        # Persist & in-memory
        if alert_id:
            dl_alerts.record_attempt(
                dl,
                alert_id=alert_id,
                channel="voice",
                provider="twilio",
                status="skipped",
            )
        mem_record_attempt(
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
        if alert_id:
            dl_alerts.record_attempt(
                dl,
                alert_id=alert_id,
                channel="voice",
                provider="twilio",
                status="success",
                http_status=http_status,
            )
            dl_alerts.touch_dispatch(dl, alert_id)
        mem_record_attempt(
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
        if alert_id:
            dl_alerts.record_attempt(
                dl,
                alert_id=alert_id,
                channel="voice",
                provider="twilio",
                status="fail",
                http_status=int(status) if status is not None else None,
                error_code=str(code) if code is not None else None,
                error_msg=str(e)[:240],
            )
        mem_record_attempt(
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
        if alert_id:
            dl_alerts.record_attempt(
                dl,
                alert_id=alert_id,
                channel="voice",
                provider="twilio",
                status="fail",
                error_msg=str(e)[:240],
            )
        mem_record_attempt(
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
