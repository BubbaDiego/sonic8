from __future__ import annotations
import json, logging, time
from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("sonic.engine")


def _load_aggregator():
    try:
        mod = import_module("backend.core.xcom_core.xcom_core")
        fn  = getattr(mod, "dispatch_notifications", None)
        return fn if callable(fn) else None
    except Exception as e:
        log.info("[xcom] aggregator import failed: %s", e)
        return None


def _load_voice():
    try:
        mod = import_module("backend.core.xcom_core.dispatch")
        fn  = getattr(mod, "dispatch_voice", None)
        return fn if callable(fn) else None
    except Exception as e:
        log.info("[xcom] voice import failed: %s", e)
        return None


def _channels_for_monitor(cfg: Dict[str, Any], name: str) -> Dict[str, bool]:
    root1 = cfg.get(f"{name}_monitor") or {}
    root2 = cfg.get(name) or {}
    if isinstance(root1, dict) and "notifications" in root1:
        notif = root1.get("notifications") or {}
    elif isinstance(root2, dict) and "notifications" in root2:
        notif = root2.get("notifications") or {}
    else:
        notif = {}
    return {"system": bool(notif.get("system")),
            "voice":  bool(notif.get("voice")),
            "sms":    bool(notif.get("sms")),
            "tts":    bool(notif.get("tts"))}


def _latest_dl_rows(dl) -> List[Dict[str, Any]]:
    mgr = getattr(dl, "dl_monitors", None) or getattr(dl, "monitors", None)
    if not mgr: return []
    getr = getattr(mgr, "get_rows", None)
    if callable(getr):
        try:
            rows = getr()
            return rows if isinstance(rows, list) else []
        except Exception as e:
            log.info("[xcom] dl_monitors.get_rows error: %s", e)
            return []
    rows = getattr(mgr, "rows", None) or getattr(mgr, "items", None)
    return rows if isinstance(rows, list) else []


def _global_snooze_seconds(cfg: Dict[str, Any]) -> int:
    mon = cfg.get("monitor") or {}
    try: return int(mon.get("global_snooze_seconds", 0))
    except Exception: return 0


def _now_ts() -> float: return time.time()
def _to_iso(ts: float) -> str: return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _get_last_sent_ts(dl) -> Optional[float]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"): return None
    v = sysmgr.get_var("xcom_last_sent_ts")
    if isinstance(v, (int,float)): return float(v)
    if isinstance(v, str):
        try: return float(v)
        except Exception: return None
    return None


def _set_last_sent_ts(dl, ts: float) -> None:
    sysmgr = getattr(dl, "system", None)
    if sysmgr and hasattr(sysmgr, "set_var"):
        sysmgr.set_var("xcom_last_sent_ts", ts)


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
    agg = _load_aggregator()
    voice = _load_voice()
    rows = _latest_dl_rows(dl)
    log.info("[xcom] bridge starting; dl_rows=%d", len(rows))

    breaches = [r for r in rows if str(r.get("state","" )).upper() == "BREACH"]
    log.info("[xcom] breaches=%d", len(breaches))
    if not breaches:
        log.info("[xcom] no-breach"); return []

    snooze = _global_snooze_seconds(cfg)
    now = _now_ts()
    last = _get_last_sent_ts(dl)
    if snooze > 0 and last is not None and (now - last) < snooze:
        log.info("[xcom] global-snooze active: last_sent=%s elapsed=%.0fs min=%ds -> SKIP",
                 _to_iso(last), now - last, snooze)
        return []

    evt = _pick_event(breaches)
    mon = (evt.get("monitor") or "").lower()
    ch  = _channels_for_monitor(cfg, mon)
    log.info("[xcom] channels(%s)=%s", mon, ch)

    if not any(ch.values()):
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
        "channels": {"system": ch.get("system"), "sms": ch.get("sms"), "tts": ch.get("tts"), "voice": False},
    }
    context = {"voice": {"tts": tts}, "dl": dl}

    sent_any = False

    # non-voice via aggregator
    if agg:
        non_voice = {"system": bool(ch.get("system")),
                     "sms":    bool(ch.get("sms")),
                     "tts":    bool(ch.get("tts")),
                     "voice":  False}
        try:
            agg(mon, payload, non_voice, context)
            log.info("[xcom] dispatched(non-voice) %s %s -> %s", mon, evt.get("label"), json.dumps(non_voice))
            sent_any = sent_any or any(non_voice.values())
        except Exception as e:
            log.info("[xcom] dispatch(non-voice) error: %s", e)

    # voice via explicit voice function (POSitional only)
    if ch.get("voice") and voice:
        try:
            voice(payload, {"voice": True}, context)  # positional
            log.info("[xcom] dispatched(voice) %s %s", mon, evt.get("label"))
            sent_any = True
        except Exception as e:
            log.info("[xcom] dispatch(voice) error: %s", e)

    if sent_any:
        _set_last_sent_ts(dl, now)
        sysmgr = getattr(dl, "system", None)
        if sysmgr and hasattr(sysmgr, "set_var"):
            sysmgr.set_var("xcom_last_sent", {
                "ts": time.time(),
                "monitor": mon,
                "label": evt.get("label"),
                "channels": ch,
                "summary": f"{mon}:{evt.get('label')} — system={ch.get('system')} voice={ch.get('voice')} sms={ch.get('sms')} tts={ch.get('tts')}"
            })
        log.info("[xcom] sent 1 notifications")
        return [{"monitor": mon, "label": evt.get("label"), "channels": ch, "result": True}]
    else:
        log.info("[xcom] sent 0 notifications")
        return []
