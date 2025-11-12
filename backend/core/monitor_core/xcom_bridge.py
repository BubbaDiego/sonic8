from __future__ import annotations
import time, json, logging, inspect
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Callable

log = logging.getLogger("sonic.engine")

# ====== Dispatcher adapter ======
# Uniform local call: send(monitor, payload, channels, context) -> Any
def _bind_dispatcher() -> Tuple[Callable[[str, dict, dict, dict], Any], str]:
    # 1) Preferred multi-channel aggregator
    try:
        from backend.core.xcom_core.xcom_core import dispatch_notifications as _agg  # type: ignore
        # Patch older voice shim to accept monitor_name if needed
        try:
            import backend.core.xcom_core.dispatch as vmod  # type: ignore
            fn = getattr(vmod, "dispatch_voice_if_needed", None)
            if callable(fn):
                params = tuple(inspect.signature(fn).parameters.keys())
                if "monitor_name" not in params:
                    _orig = fn
                    def _patched(*, monitor_name=None, payload=None, channels=None, context=None, **kw):
                        return _orig(payload=payload, channels=channels, context=context)
                    setattr(vmod, "dispatch_voice_if_needed", _patched)
                    log.info("[xcom] patched voice shim for aggregator compatibility (added monitor_name kw)")
        except Exception:
            pass
        def _send(mon: str, payload: dict, channels: dict, context: dict):
            return _agg(mon, payload, channels, context)
        return _send, "aggregator:xcom_core"
    except Exception:
        pass

    # 2) Older aggregator path
    try:
        from backend.core.xcom_core.dispatcher import dispatch_notifications as _agg2  # type: ignore
        def _send(mon: str, payload: dict, channels: dict, context: dict):
            return _agg2(mon, payload, channels, context)
        return _send, "aggregator:dispatcher"
    except Exception:
        pass

    # 3) Voice-only shim; adapt signature
    try:
        from backend.core.xcom_core.dispatch import dispatch_voice_if_needed as _voice  # type: ignore
        def _send(mon: str, payload: dict, channels: dict, context: dict):
            return _voice(payload=payload, channels=channels, context=context)
        return _send, "voice-only"
    except Exception:
        pass

    # 4) No dispatcher available
    def _noop(mon: str, payload: dict, channels: dict, context: dict):
        return {"ok": False, "reason": "no-dispatcher"}
    return _noop, "noop"

# ====== Config helpers ======
def _channels_for_monitor(cfg: Dict[str, Any], name: str) -> Dict[str, bool]:
    """
    Prefer <name>_monitor.notifications when present; otherwise <name>.notifications.
    """
    root1 = cfg.get(f"{name}_monitor") or {}
    root2 = cfg.get(name) or {}
    if isinstance(root1, dict) and "notifications" in root1:
        notif = root1.get("notifications") or {}
    elif isinstance(root2, dict) and "notifications" in root2:
        notif = root2.get("notifications") or {}
    else:
        notif = {}
    return {
        "system": bool(notif.get("system")),
        "voice":  bool(notif.get("voice")),
        "sms":    bool(notif.get("sms")),
        "tts":    bool(notif.get("tts")),
    }

def _global_snooze_seconds(cfg: Dict[str, Any]) -> int:
    """
    One global snooze window (seconds). Default = 0 (OFF) for 'amazingly simple'.
    """
    mon = cfg.get("monitor") or {}
    try:
        return int(mon.get("global_snooze_seconds", 0))
    except Exception:
        return 0

# ====== DL helpers ======
def _latest_dl_rows(dl) -> List[Dict[str, Any]]:
    mm = getattr(dl, "dl_monitors", None) or getattr(dl, "monitors", None)
    if not mm:
        return []
    for meth in ("get_rows", "latest", "list", "all"):
        fn = getattr(mm, meth, None)
        if callable(fn):
            try:
                got = fn()
                return got if isinstance(got, list) else []
            except Exception:
                continue
    arr = getattr(mm, "rows", None) or getattr(mm, "items", None)
    return list(arr) if isinstance(arr, list) else []

def _now_ts() -> float:
    return time.time()

def _to_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

def _get_last_sent_ts(dl) -> Optional[float]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"):
        return None
    v = sysmgr.get_var("xcom_last_sent_ts")
    if isinstance(v, (int,float)):
        return float(v)
    if isinstance(v, str):
        # tolerate persisted string (epoch)
        try: return float(v)
        except Exception: return None
    return None

def _set_last_sent_ts(dl, ts: float) -> None:
    sysmgr = getattr(dl, "system", None)
    if sysmgr and hasattr(sysmgr, "set_var"):
        sysmgr.set_var("xcom_last_sent_ts", ts)

# ====== Bridge ======
def _compose_text(row: Dict[str, Any]) -> Tuple[str, str, str]:
    mon  = (row.get("monitor") or "").lower()
    lab  = row.get("label","")
    val  = row.get("value")
    thrv = row.get("thr_value")
    thro = row.get("thr_op") or ""
    src  = (row.get("meta") or {}).get("limit_source") or row.get("source") or mon
    vtxt = f"{val:.2f}" if isinstance(val,(int,float)) else str(val or "-")
    ttxt = f"{thro} {thrv:.2f}" if isinstance(thrv,(int,float)) else "-"
    subj = f"[{mon.upper()}] {lab} BREACH"
    body = f"{lab}: value={vtxt} threshold={ttxt} source={src}"
    tts  = f"{lab} breach. Value {vtxt} vs threshold {ttxt}."
    return subj, body, tts

def _pick_event(breaches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pick one event to announce (simple & predictable):
    priority by monitor: liquid > profit > market > price, preserve row order otherwise.
    """
    priority = {"liquid": 0, "profit": 1, "market": 2, "price": 3}
    return sorted(breaches, key=lambda r: (priority.get((r.get("monitor") or "").lower(), 99)))[0]

def dispatch_breaches_from_dl(dl, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    send, mode = _bind_dispatcher()
    log.info("[xcom] dispatcher mode=%s", mode)

    rows = _latest_dl_rows(dl)
    log.info("[xcom] bridge starting; dl_rows=%d", len(rows))

    # filter BREACH rows
    breaches = [r for r in rows if (str(r.get("state") or "").upper() == "BREACH")]
    log.info("[xcom] breaches=%d", len(breaches))
    if not breaches:
        log.info("[xcom] no-breach")
        return []

    # global snooze (simple & reliable)
    snooze = _global_snooze_seconds(cfg)
    now = _now_ts()
    last = _get_last_sent_ts(dl)
    if snooze > 0 and last is not None:
        elapsed = now - last
        if elapsed < snooze:
            log.info("[xcom] global-snooze active: last_sent=%s elapsed=%.0fs min=%ds -> SKIP",
                     _to_iso(last), elapsed, snooze)
            return []

    # pick one event and channels (from JSON)
    evt = _pick_event(breaches)
    mon = (evt.get("monitor") or "").lower()

    channels = _channels_for_monitor(cfg, mon)
    log.info("[xcom] channels(%s)=%s", mon, channels)
    if not any(channels.values()):
        log.info("[xcom] channels disabled -> SKIP")
        return []

    # Compose and send once
    subj, body, tts = _compose_text(evt)
    payload = {
        "breach": True,
        "monitor": mon,
        "label": evt.get("label"),
        "value": evt.get("value"),
        "threshold": {"op": evt.get("thr_op"), "value": evt.get("thr_value")},
        "source": (evt.get("meta") or {}).get("limit_source") or evt.get("source"),
        "cycle_id": evt.get("cycle_id"),
        "subject": subj,
        "body": body,
    }
    context = {
        "voice": {"tts": tts},
        "dl": dl,
    }

    try:
        result = send(mon, payload, channels, context)
        # mark global last-sent on success path (don't overthink result shape)
        _set_last_sent_ts(dl, now)
        log.info("[xcom] dispatched %s %s -> %s", mon, evt.get("label"), json.dumps(channels))
        return [{"monitor": mon, "label": evt.get("label"), "channels": channels, "result": result}]
    except Exception as e:
        log.info("[xcom] dispatch error for %s %s: %s", mon, evt.get("label"), e)
        return []


__all__ = ["dispatch_breaches_from_dl"]
