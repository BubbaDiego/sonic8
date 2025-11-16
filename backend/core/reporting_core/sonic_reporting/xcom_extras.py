from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

# Optional: repo-local DataLocker. Keep guarded to avoid hard import failures.
try:
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:  # pragma: no cover
    DataLocker = None  # type: ignore

MONITOR_NAME = os.getenv("SONIC_MONITOR_NAME", "sonic_monitor")
DEFAULT_INTERVAL = 60  # fallback if nothing else resolves


# ------------------------------- utils ----------------------------------------

def _dl_or_singleton(dl: Any | None) -> Any | None:
    if dl is not None:
        return dl
    if DataLocker:
        try:
            return DataLocker.get_instance()
        except Exception:
            return None
    return None

def _fmt_hms(seconds: int) -> str:
    s = max(0, int(seconds))
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def _parse_epoch_or_iso(val: Any) -> Optional[float]:
    """Accept epoch number/str or ISO8601 (Z/offset). Return epoch seconds."""
    try:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        if s.replace(".", "", 1).isdigit():
            return float(s)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def append_xcom_history(dl: Any, event: Dict[str, Any], max_len: int = 20) -> None:
    """Persist a rolling buffer of the most recent XCom events in system vars."""

    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var") or not hasattr(sysmgr, "set_var"):
        return

    try:
        history = sysmgr.get_var("xcom_history")
    except Exception:
        history = None

    if not isinstance(history, list):
        history = []

    history.append(event)
    if len(history) > max_len:
        history = history[-max_len:]

    try:
        sysmgr.set_var("xcom_history", history)
    except Exception:
        # Never let history persistence break the dispatcher / bridge.
        pass

def _as_bool(val) -> tuple[bool, bool]:
    if isinstance(val, bool): return True, val
    if isinstance(val, (int, float)): return True, bool(val)
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("1","true","on","yes","y"):  return True, True
        if v in ("0","false","off","no","n"): return True, False
    return False, False


# ------------------------ config helpers (FILE) -------------------------------

def _loop_seconds_from_cfg(cfg: dict | None) -> Optional[int]:
    if not isinstance(cfg, dict):
        return None
    mon = (cfg.get("monitor") or {})
    for key in ("loop_seconds", "interval_seconds"):
        if key in mon:
            try:
                iv = int(mon.get(key))
                if iv > 0:
                    return iv
            except Exception:
                pass
    return None

def _xcom_from_cfg(cfg: dict | None) -> tuple[Optional[bool], str]:
    """Return (bool or None, src_label) from explicit config dict."""
    if not isinstance(cfg, dict):
        return None, "—"
    mon = (cfg.get("monitor") or {})
    if "xcom_live" in mon:
        ok, b = _as_bool(mon.get("xcom_live"))
        if ok: return b, "FILE"
    for section in ("liquid", "profit", "market", "price"):
        block = cfg.get(section) or {}
        notif = block.get("notifications") if isinstance(block, dict) else None
        if isinstance(notif, dict) and "voice" in notif:
            ok, b = _as_bool(notif.get("voice"))
            if ok:
                return b, f"FILE:{section}.notifications"
    ch = (cfg.get("channels") or {})
    voice = ch.get("voice") or ch.get("xcom") or {}
    if "enabled" in voice:
        ok, b = _as_bool(voice.get("enabled"))
        if ok: return b, "FILE"
    return None, "—"

def get_default_voice_cooldown(cfg: dict | None = None) -> int:
    """default seconds for voice call cooldown (UI shows this when idle)."""
    # 1) JSON: channels.voice.cooldown_seconds
    try:
        if isinstance(cfg, dict):
            ch = cfg.get("channels") or {}
            v = ch.get("voice") or {}
            val = v.get("cooldown_seconds")
            if val is not None:
                n = int(val)
                if n >= 0:
                    return n
    except Exception:
        pass
    # 2) ENV override
    try:
        env = os.getenv("VOICE_COOLDOWN_SECONDS", "").strip()
        if env.isdigit():
            n2 = int(env)
            if n2 >= 0:
                return n2
    except Exception:
        pass
    # 3) fallback
    return 180


# ------------------------------ public API ------------------------------------

def get_sonic_interval(dl: Any | None = None) -> int:
    """
    Poll interval (seconds) precedence:
      1) FILE: cfg.monitor.loop_seconds (JSON-only friendly)
      2) DB: monitor_heartbeat.interval_seconds for MONITOR_NAME
      3) ENV: SONIC_MONITOR_INTERVAL or MONITOR_LOOP_SECONDS
      4) DEFAULT: 60
    """
    locker = _dl_or_singleton(dl)

    # 1) FILE (JSON)
    try:
        cfg = getattr(locker, "global_config", None)
        iv = _loop_seconds_from_cfg(cfg)
        if iv:
            return iv
    except Exception:
        pass

    # 2) DB (monitor_heartbeat)
    try:
        cur = getattr(getattr(locker, "db", None), "get_cursor", lambda: None)()
        if cur is not None:
            cur.execute(
                "SELECT interval_seconds FROM monitor_heartbeat WHERE monitor_name=?",
                (MONITOR_NAME,),
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                iv2 = int(row[0])
                if iv2 > 0:
                    return iv2
    except Exception:
        pass

    # 3) ENV
    for env_name in ("SONIC_MONITOR_INTERVAL", "MONITOR_LOOP_SECONDS"):
        try:
            val = os.getenv(env_name, "").strip()
            if val.isdigit():
                iv3 = int(val)
                if iv3 > 0:
                    return iv3
        except Exception:
            pass

    # 4) DEFAULT
    return int(DEFAULT_INTERVAL)


def read_snooze_remaining(dl: Any | None = None) -> Tuple[int, Optional[float]]:
    """
    Remaining snooze seconds and ETA epoch.

    Priority:
      1) system.liquid_snooze_until / system.global_snooze_until (epoch/ISO)
      2) last alert + configured 'snooze_seconds' in system['liquid_monitor']
    """
    now = time.time()
    try:
        locker = _dl_or_singleton(dl)
        sysvars = getattr(locker, "system", None)
        if not sysvars:
            return 0, None

        until = sysvars.get_var("liquid_snooze_until") or sysvars.get_var("global_snooze_until")
        ts = _parse_epoch_or_iso(until)
        if ts:
            rem = int(ts - now)
            return (rem if rem > 0 else 0), (ts if rem > 0 else None)

        liq_cfg = sysvars.get_var("liquid_monitor") or {}
        last = liq_cfg.get("_last_alert_ts")
        snooze = int(liq_cfg.get("snooze_seconds", 0) or 0)
        if last and snooze > 0:
            ts2 = float(last) + float(snooze)
            rem2 = int(ts2 - now)
            return (rem2 if rem2 > 0 else 0), (ts2 if rem2 > 0 else None)
    except Exception:
        pass
    return 0, None


def read_voice_cooldown_remaining(dl: Any | None = None) -> Tuple[int, Optional[float]]:
    """
    Remaining voice-call cooldown seconds and ETA epoch.
    Based on system.voice_cooldown_until (epoch/ISO); returns (0, None) if idle.
    """
    now = time.time()
    try:
        locker = _dl_or_singleton(dl)
        sysvars = getattr(locker, "system", None)
        if not sysvars:
            return 0, None
        until = sysvars.get_var("voice_cooldown_until")
        ts = _parse_epoch_or_iso(until)
        if ts:
            rem = int(ts - now)
            return (rem if rem > 0 else 0), (ts if rem > 0 else None)
    except Exception:
        pass
    return 0, None


def set_voice_cooldown(dl: Any | None, seconds: int) -> None:
    """Start (or clear with seconds<=0) the voice-call cooldown window."""
    try:
        locker = _dl_or_singleton(dl)
        sysvars = getattr(locker, "system", None)
        if not sysvars:
            return
        if seconds and seconds > 0:
            sysvars.set_var("voice_cooldown_until", time.time() + float(seconds))
        else:
            sysvars.set_var("voice_cooldown_until", None)
    except Exception:
        pass


def render_under_xcom_live(
    dl: Any | None = None,
    *,
    emit: Callable[[str], None] = print,
) -> None:
    """
    Print the rows under '📡 XCOM Live' in the Sync Data table:

        ⏱  Loop interval     ✅ 30s            Runtime · live loop
        🔕 Alert snooze      🟡 3:14           until 10:43am
        🔔 Voice cooldown    🟡 2:05           until 10:44am   |  or ✅ idle  default 180s
    """
    ACT_W = 24
    STAT_W = 11  # a tad wider to keep columns aligned

    def row(activity: str, status: str, details: str) -> str:
        a = activity.ljust(ACT_W)
        s = status.ljust(STAT_W)
        return f"  {a} {s} {details}"

    # ⏱ Loop interval
    iv = get_sonic_interval(dl)
    emit(row("⏱  Loop interval", f"✅ {iv}s", "Runtime · live loop"))

    # 🔕 Alert snooze
    rem, eta = read_snooze_remaining(dl)
    if rem > 0:
        try:
            dt = datetime.fromtimestamp(eta, tz=timezone.utc).astimezone() if eta else None
            eta_s = (dt.strftime("%I:%M%p").lstrip("0").lower()) if dt else ""
        except Exception:
            eta_s = ""
        emit(row("🔕 Alert snooze", f"🟡 {_fmt_hms(rem)}", f"until {eta_s}" if eta_s else "—"))
    else:
        emit(row("🔕 Alert snooze", "✅ disabled", "—"))

    # 🔔 Voice cooldown
    vrem, veta = read_voice_cooldown_remaining(dl)
    if vrem > 0:
        try:
            dt2 = datetime.fromtimestamp(veta, tz=timezone.utc).astimezone() if veta else None
            eta2 = (dt2.strftime("%I:%M%p").lstrip("0").lower()) if dt2 else ""
        except Exception:
            eta2 = ""
        emit(row("🔔 Voice cooldown", f"🟡 {_fmt_hms(vrem)}", f"until {eta2}" if eta2 else "—"))
    else:
        cfg = getattr(_dl_or_singleton(dl), "global_config", None)
        default_cd = get_default_voice_cooldown(cfg)
        emit(row("🔔 Voice cooldown", "✅ idle", f"default {default_cd}s"))


def xcom_live_status(dl=None, cfg: dict | None = None) -> tuple[bool, str]:
    """
    Unified XCOM status probe:
      1) RUNTIME (voice/xcom services on DataLocker)
      2) FILE (explicit cfg dict if given)
      3) FILE (dl.global_config)
      4) DB    (system vars)
      5) ENV   (XCOM_LIVE / XCOM_ACTIVE)
    """
    # 1) RUNTIME
    try:
        for name in ("voice_service","xcom_voice","xcom","voice"):
            svc = getattr(dl, name, None)
            if svc is None:
                continue
            for key in ("is_live","live","enabled","is_enabled","active","is_active"):
                try:
                    v = getattr(svc, key) if not isinstance(svc, dict) else svc.get(key)
                    if callable(v): v = v()
                    ok, b = _as_bool(v)
                    if ok: return b, "RUNTIME"
                except Exception:
                    pass
    except Exception:
        pass

    # 2) FILE (explicit)
    b, src = _xcom_from_cfg(cfg)
    if b is not None:
        return bool(b), src

    # 3) FILE (dl.global_config)
    try:
        b2, src2 = _xcom_from_cfg(getattr(dl, "global_config", None) or {})
        if b2 is not None:
            return bool(b2), src2
    except Exception:
        pass

    # 4) DB
    try:
        sysvars = getattr(dl, "system", None)
        if sysvars:
            var = (sysvars.get_var("xcom") or {})
            for key in ("live","is_live","enabled","is_enabled","active"):
                if key in var:
                    ok, b = _as_bool(var.get(key))
                    if ok: return b, "DB"
    except Exception:
        pass

    # 5) ENV
    env = os.getenv("XCOM_LIVE", os.getenv("XCOM_ACTIVE", ""))
    ok, b = _as_bool(env)
    if ok:
        return b, "ENV"

    return False, "—"


def xcom_ready(dl=None, *, cfg: dict | None = None) -> tuple[bool, str]:
    """
    True when outbound alerts are allowed **right now**:
      - XCOM Live is ON (file/db/env)
      - global snooze is not active
      - voice cooldown is not active
    """
    live, src = xcom_live_status(dl, cfg)
    if not live:
        return False, f"xcom_off[{src}]"
    rem, _ = read_snooze_remaining(dl)
    if rem > 0:
        return False, f"snoozed({rem}s)"
    vrem, _ = read_voice_cooldown_remaining(dl)
    if vrem > 0:
        return False, f"voice_cooldown({vrem}s)"
    return True, "ok"


def xcom_guard(dl, *, triggered: bool, cfg: dict | None = None) -> tuple[bool, str]:
    """
    Full notify gate for monitors:
      - requires a real breach (triggered=True), and
      - passes xcom_ready() checks.
    """
    if not triggered:
        return False, "not_triggered"
    return xcom_ready(dl, cfg=cfg)
