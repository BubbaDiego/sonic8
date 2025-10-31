# -*- coding: utf-8 -*-
"""Shared helpers for Sonic/XCom status checks used by reporting and monitors."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Optional
import math
import os


_BOOL_TRUE = {"1", "true", "yes", "on", "y", "enabled", "active"}
_BOOL_FALSE = {"0", "false", "no", "off", "n", "disabled", "inactive"}


def _as_bool(value: Any) -> tuple[bool, bool]:
    """Return ``(is_boolean_like, value)`` for loose truthy / falsy inputs."""

    if isinstance(value, bool):
        return True, value
    if isinstance(value, (int, float)):
        return True, bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _BOOL_TRUE:
            return True, True
        if text in _BOOL_FALSE:
            return True, False
    return False, False


def _probe_obj_bool(obj: Any, names: Iterable[str]) -> Optional[bool]:
    for name in names:
        try:
            attr = getattr(obj, name)
        except Exception:  # pragma: no cover - defensive
            attr = None
        ok, value = _as_bool(attr)
        if ok:
            return value
        if callable(attr):
            try:
                result = attr()
            except Exception:  # pragma: no cover - defensive
                result = None
            ok_call, value_call = _as_bool(result)
            if ok_call:
                return value_call
    return None


def _coerce_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            dt = datetime.fromisoformat(text)
        except Exception:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def xcom_live_status(dl=None, cfg: dict | None = None) -> tuple[bool, str]:
    """Return ``(is_live, origin)`` probing runtime, config, DB, env in that order."""

    # 1) Runtime hooks on the DataLocker instance
    if dl is not None:
        try:
            for name in ("voice_service", "xcom_voice", "xcom", "voice"):
                svc = getattr(dl, name, None)
                if not svc:
                    continue
                value = _probe_obj_bool(
                    svc,
                    ("is_live", "live", "enabled", "is_enabled", "active", "is_active"),
                )
                if value is not None:
                    return bool(value), "RUNTIME"
                if isinstance(svc, dict):
                    for key in ("enabled", "is_enabled", "active", "live", "is_live"):
                        if key in svc:
                            ok, b = _as_bool(svc.get(key))
                            if ok:
                                return b, "RUNTIME"
        except Exception:  # pragma: no cover - defensive
            pass

    # 2) Explicit config (passed in or hanging off the DataLocker)
    cfg_obj: dict[str, Any] | None = cfg if isinstance(cfg, dict) else None
    if cfg_obj is None and dl is not None:
        maybe_cfg = getattr(dl, "global_config", None)
        if isinstance(maybe_cfg, dict):
            cfg_obj = maybe_cfg
    if cfg_obj:
        try:
            monitor_section = cfg_obj.get("monitor") if isinstance(cfg_obj, dict) else None
            if isinstance(monitor_section, dict):
                ok, value = _as_bool(monitor_section.get("xcom_live"))
                if ok:
                    return value, "FILE"
            # voice channel overrides in the same config blob
            channels = cfg_obj.get("channels") if isinstance(cfg_obj, dict) else None
            voice = {}
            if isinstance(channels, dict):
                voice = channels.get("voice") or channels.get("xcom") or {}
            if isinstance(voice, dict):
                for key in ("enabled", "active", "live", "is_live", "is_enabled"):
                    if key in voice:
                        ok, value = _as_bool(voice.get(key))
                        if ok:
                            return value, "FILE"
        except Exception:  # pragma: no cover - defensive
            pass

    # 3) System vars / DB backing store
    if dl is not None:
        try:
            sysvars = getattr(dl, "system", None)
            if sysvars:
                var = sysvars.get_var("xcom") or {}
                if isinstance(var, dict):
                    for key in ("live", "is_live", "enabled", "is_enabled", "active"):
                        if key in var:
                            ok, value = _as_bool(var.get(key))
                            if ok:
                                return value, "DB"
        except Exception:  # pragma: no cover - defensive
            pass

    # 4) Environment fallbacks
    for env_key in ("SONIC_XCOM_LIVE", "XCOM_LIVE", "XCOM_ACTIVE"):
        ok, value = _as_bool(os.getenv(env_key))
        if ok:
            return value, "ENV"

    return False, "—"


def render_under_xcom_live(
    dl,
    renderer: Callable[[bool, str], Any],
    *,
    cfg: dict | None = None,
) -> Any:
    """Invoke ``renderer`` with ``(is_live, origin)`` information."""

    live, src = xcom_live_status(dl, cfg=cfg)
    return renderer(live, src)


def get_sonic_interval(dl=None) -> int:
    """Best-effort fetch of the active Sonic loop interval in seconds."""

    # 1) Runtime system override (most accurate)
    if dl is not None:
        try:
            sysvars = getattr(dl, "system", None)
            if sysvars:
                raw = sysvars.get_var("sonic_monitor_loop_time")
                if raw:
                    seconds = int(float(raw))
                    if seconds > 0:
                        return seconds
        except Exception:  # pragma: no cover - defensive
            pass
        try:
            cfg_obj = getattr(dl, "global_config", None)
            if isinstance(cfg_obj, dict):
                monitor_section = cfg_obj.get("monitor") or {}
                seconds = monitor_section.get("loop_seconds")
                if seconds is not None:
                    seconds = int(float(seconds))
                    if seconds > 0:
                        return seconds
        except Exception:
            pass
        try:
            db = getattr(dl, "db", None)
            cursor = db.get_cursor() if db else None
            if cursor:
                cursor.execute(
                    "SELECT interval_seconds FROM monitor_heartbeat WHERE monitor_name = ?",
                    ("sonic_monitor",),
                )
                row = cursor.fetchone()
                if row and row[0] is not None:
                    seconds = int(float(row[0]))
                    if seconds > 0:
                        return seconds
        except Exception:  # pragma: no cover - defensive
            pass

    # 2) JSON config on disk
    try:
        from backend.core.config.json_config import load_config as _load_json_cfg  # type: ignore

        cfg = _load_json_cfg()
        seconds = int(float(cfg.get("system_config", {}).get("sonic_monitor_loop_time", 0) or 0))
        if seconds > 0:
            return seconds
    except Exception:
        pass

    # 3) Environment override
    env_raw = os.getenv("SONIC_MONITOR_LOOP_SECONDS")
    if env_raw:
        try:
            seconds = int(float(env_raw))
            if seconds > 0:
                return seconds
        except Exception:
            pass

    # 4) Sonic monitor defaults
    try:
        from backend.core.monitor_core.sonic_monitor import DEFAULT_INTERVAL, LOOP_SECONDS  # type: ignore

        seconds = int(float(LOOP_SECONDS or DEFAULT_INTERVAL))
        if seconds > 0:
            return seconds
    except Exception:
        pass

    return 60


def read_snooze_remaining(dl=None) -> tuple[int, Optional[int]]:
    """Return ``(seconds_remaining, eta_epoch)`` for the global snooze timer."""

    now = datetime.now(timezone.utc)
    until: Optional[datetime] = None

    if dl is not None:
        try:
            sysvars = getattr(dl, "system", None)
            if sysvars:
                raw = sysvars.get_var("snooze_until")
                until = _coerce_dt(raw)
        except Exception:  # pragma: no cover - defensive
            until = until or None

    if until is None and dl is not None:
        until = _coerce_dt(getattr(dl, "snooze_until", None))

    if until is None:
        raw_env = os.getenv("SONIC_SNOOZE_UNTIL")
        if raw_env:
            until = _coerce_dt(raw_env)

    if until and until < now:
        until = None

    if not until:
        return 0, None

    remaining = max(0, int(math.ceil((until - now).total_seconds())))
    eta = int(until.timestamp()) if remaining > 0 else None
    return remaining, eta


def xcom_ready(dl=None, *, cfg: dict | None = None) -> tuple[bool, str]:
    """True when XCom can notify right now (live & not snoozed)."""

    live, src = xcom_live_status(dl, cfg)
    if not live:
        return False, f"xcom_off[{src}]"
    remaining, _ = read_snooze_remaining(dl)
    if remaining > 0:
        return False, f"snoozed({remaining}s)"
    return True, "ok"


def xcom_guard(dl, *, triggered: bool, cfg: dict | None = None) -> tuple[bool, str]:
    """Require a trigger and XCom readiness before sending notifications."""

    if not triggered:
        return False, "not_triggered"
    ok, why = xcom_ready(dl, cfg=cfg)
    if not ok:
        return False, why
    return True, "ok"


__all__ = [
    "render_under_xcom_live",
    "get_sonic_interval",
    "read_snooze_remaining",
    "xcom_live_status",
    "xcom_ready",
    "xcom_guard",
]
