from __future__ import annotations
import time, json, logging, inspect, importlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Callable

log = logging.getLogger("sonic.engine")

# ====== dispatcher adapter (uniform local API) ======
# send_agg(mon, payload, channels, context) -> Any  (non-voice only)
# send_voice(payload, channels, context) -> Any     (voice only; legacy signature)
def _bind_dispatchers() -> Tuple[Callable[[str,dict,dict,dict],Any], Callable[[dict,dict,dict],Any], str]:
    """
    Returns (send_agg, send_voice, mode)
      - send_agg handles system/sms/tts via aggregator (voice removed)
      - send_voice calls the legacy voice shim directly with the *old* signature
      - mode is for logging/diagnostics
    """

    # -------- voice shim (old signature we can always call) --------
    _voice_fn = None
    _voice_mode = "none"

    # most trees
    try:
        vmod = importlib.import_module("backend.core.xcom_core.dispatch")
        fn = getattr(vmod, "dispatch_voice_if_needed", None)
        if callable(fn):
            params = tuple(inspect.signature(fn).parameters.keys())
            # legacy shim does NOT have 'monitor_name'
            if "monitor_name" in params:
                # wrap to ignore monitor_name if someone calls with it
                _orig = fn
                def _voice_compat(*, monitor_name=None, payload=None, channels=None, context=None, **kw):
                    return _orig(payload=payload, channels=channels, context=context)
                setattr(vmod, "dispatch_voice_if_needed", _voice_compat)
                _voice_fn = getattr(vmod, "dispatch_voice_if_needed")
                _voice_mode = "voice:wrapped"
                log.info("[xcom] patched voice shim (ignored monitor_name)")
            else:
                _voice_fn = fn
                _voice_mode = "voice:legacy"
    except Exception:
        pass

    # if still none, install a no-op voice fn (so calling code is simple)
    if not callable(_voice_fn):
        def _voice_fn(payload=None, channels=None, context=None):  # type: ignore
            return {"ok": False, "reason": "no-voice-shim"}
        _voice_mode = "voice:noop"

    # -------- aggregator (for non-voice) --------
    _agg_fn = None
    _mode = "noop"
    try:
        amod = importlib.import_module("backend.core.xcom_core.xcom_core")
        agg = getattr(amod, "dispatch_notifications", None)
        if callable(agg):
            _agg_fn = agg
            _mode = "aggregator:xcom_core"
        else:
            raise ImportError
    except Exception:
        try:
            dmod = importlib.import_module("backend.core.xcom_core.dispatcher")
            agg2 = getattr(dmod, "dispatch_notifications", None)
            if callable(agg2):
                _agg_fn = agg2
                _mode = "aggregator:dispatcher"
        except Exception:
            _agg_fn = None
            _mode = "noop"

    # normalize to our local APIs
    def send_agg(mon: str, payload: dict, channels: dict, context: dict):
        if not callable(_agg_fn):
            return {"ok": False, "reason": "no-aggregator"}
        # enforce non-voice for aggregator (split path)
        ch = dict(channels or {})
        ch["voice"] = False
        return _agg_fn(mon, payload, ch, context)

    def send_voice(payload: dict, channels: dict, context: dict):
        # pass *only* the legacy signature
        return _voice_fn(payload=payload, channels=channels, context=context)  # type: ignore

    log.info("[xcom] dispatcher mode=%s %s", _mode, _voice_mode)
    return send_agg, send_voice, f"{_mode}|{_voice_mode}"

# ====== config helpers ======
def _channels_for_monitor(cfg: Dict[str, Any], name: str) -> Dict[str, bool]:
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
    mon = cfg.get("monitor") or {}
    try:
        return int(mon.get("global_snooze_seconds", 0))  # 0 = OFF
    except Exception:
        return 0

# ====== DL helpers ======
def _latest_dl_rows(dl) -> List[Dict[str, Any]]:
    mm = getattr(dl, "dl_monitors", None) or getattr(dl, "monitors", None)
    if not mm: return []
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
        try: return float(v)
        except Exception: return None
    return None

def _set_last_sent_ts(dl, ts: float) -> None:
    sysmgr = getattr(dl, "system", None)
    if sysmgr and hasattr(sysmgr, "set_var"):
        sysmgr.set_var("xcom_last_sent_ts", ts)

# ====== bridge ======
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
    priority = {"liquid": 0, "profit": 1, "market": 2, "price": 3}
    return sorted(breaches, key=lambda r: (priority.get((r.get("monitor") or "").lower(), 99)))[0]

def dispatch_breaches_from_dl(dl, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    send_agg, send_voice, mode = _bind_dispatchers()

    rows = _latest_dl_rows(dl)
    log.info("[xcom] bridge starting; dl_rows=%d", len(rows))

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

    # pick one event; select channels from JSON
    evt = _pick_event(breaches)
    mon = (evt.get("monitor") or "").lower()
    channels = _channels_for_monitor(cfg, mon)
    log.info("[xcom] channels(%s)=%s", mon, channels)
    if not any(channels.values()):
        log.info("[xcom] channels disabled -> SKIP")
        return []

    subj, body, tts = _compose_text(evt)
    payload = {
        "breach": True, "monitor": mon, "label": evt.get("label"),
        "value": evt.get("value"),
        "threshold": {"op": evt.get("thr_op"), "value": evt.get("thr_value")},
        "source": (evt.get("meta") or {}).get("limit_source") or evt.get("source"),
        "cycle_id": evt.get("cycle_id"),
        "subject": subj, "body": body,
    }
    context = {"voice": {"tts": tts}, "dl": dl}

    # split send: aggregator for non-voice, shim for voice
    sent_any = False

    # non-voice bundle
    non_voice = {k: v for k, v in channels.items() if k != "voice"}
    if any(non_voice.values()):
        try:
            res = send_agg(mon, payload, non_voice, context)
            log.info("[xcom] dispatched(non-voice) %s %s -> %s", mon, evt.get("label"), json.dumps(non_voice))
            sent_any = True
        except Exception as e:
            log.info("[xcom] dispatch(non-voice) error: %s", e)

    # voice separately (legacy signature)
    if channels.get("voice", False):
        try:
            res_v = send_voice(payload, {"voice": True}, context)
            log.info("[xcom] dispatched(voice) %s %s", mon, evt.get("label"))
            sent_any = True
        except Exception as e:
            log.info("[xcom] dispatch(voice) error: %s", e)

    if sent_any:
        _set_last_sent_ts(dl, now)
        log.info("[xcom] sent 1 notifications")  # one umbrella send per cycle by design
        return [{"monitor": mon, "label": evt.get("label"), "channels": channels, "result": True}]
    else:
        log.info("[xcom] sent 0 notifications")
        return []


__all__ = ["dispatch_breaches_from_dl"]
