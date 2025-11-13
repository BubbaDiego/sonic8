from __future__ import annotations
import json, logging, time
from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional, Tuple

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


def _bind_dispatcher() -> Tuple[Callable[[str, Dict[str, Any], Dict[str, bool], Dict[str, Any]], Dict[str, Any]], str]:
    agg = _load_aggregator()
    voice = _load_voice()

    mode_parts: List[str] = []
    if agg:
        mode_parts.append("agg")
    if voice:
        mode_parts.append("voice")
    if not mode_parts:
        mode_parts.append("noop")

    def _send(mon: str, payload: Dict[str, Any], channels: Dict[str, bool], context: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {"ok": False}
        sent = False
        payload_with_channels = {**payload, "channels": channels}

        if agg:
            non_voice = {"system": bool(channels.get("system")),
                         "sms":    bool(channels.get("sms")),
                         "tts":    bool(channels.get("tts")),
                         "voice":  False}
            if any(non_voice.values()):
                agg_result = agg(mon, payload_with_channels, non_voice, context)
                result["non_voice"] = agg_result
                if isinstance(agg_result, dict):
                    sent = sent or bool(agg_result.get("ok")) or bool(agg_result)
                else:
                    sent = sent or bool(agg_result)

        if voice and bool(channels.get("voice")):
            voice_result = voice(payload_with_channels, {"voice": True}, context)
            result["voice"] = voice_result
            if isinstance(voice_result, dict):
                sent = sent or bool(voice_result.get("ok")) or bool(voice_result)
            else:
                sent = sent or bool(voice_result)

        result["ok"] = sent
        return result

    return _send, "+".join(mode_parts)


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


def _require_voice_provider(dl) -> Tuple[Dict[str, Any], List[str]]:
    """
    Load voice provider from DL.system['xcom_providers'] and validate required keys.
    Returns (voice_cfg, missing_keys_list).
    """
    sysmgr = getattr(dl, "system", None)
    prov = sysmgr.get_var("xcom_providers") if sysmgr and hasattr(sysmgr, "get_var") else None
    voice = (prov or {}).get("voice") or {}
    missing: List[str] = []

    provider = (voice.get("provider") or "").strip().lower()
    if not provider:
        missing.append("provider")

    if not voice.get("from"):
        missing.append("from")

    if provider == "twilio":
        if not voice.get("account_sid"):
            missing.append("account_sid")
        if not voice.get("auth_token"):
            missing.append("auth_token")
        dest = voice.get("to")
        if not dest or (isinstance(dest, list) and not dest) or (isinstance(dest, str) and not dest.strip()):
            missing.append("to")

    return voice, missing


def dispatch_breaches_from_dl(dl, cfg: dict) -> List[Dict[str, Any]]:
    """
    DL-first XCom bridge.
    - Reads dl_monitors latest rows
    - Triggers on BREACH
    - Uses JSON channels
    - Enforces per-monitor snooze
    - Validates provider config; if missing, writes error + emits system notification
    - Uses multi-channel dispatcher via _bind_dispatcher()
    """
    send, mode = _bind_dispatcher()
    log.info("[xcom] dispatcher mode=%s", mode)

    rows = _latest_dl_rows(dl)
    log.info("[xcom] bridge starting; dl_rows=%d", len(rows))

    _body_cfg = cfg.get("liquid_monitor", {})
    out: List[Dict[str, Any]] = []
    now = time.time()

    breaches = [r for r in (rows or []) if str(r.get("state", "")).upper() == "BREACH"]
    log.info("[xcom] breaches=%d", len(breaches))

    for r in breaches:
        mon = (r.get("monitor") or "").lower()
        label = r.get("label") or ""
        if mon not in ("liquid", "profit", "market", "price"):
            continue

        channels = _channels_for_monitor(cfg, mon)
        if not any(channels.values()):
            continue

        snooze_cfg = (cfg.get(f"{mon}_monitor") or cfg.get(mon) or {})
        default_snooze = 600 if mon != "profit" else 1200
        try:
            snooze_s = _global_saturation = int(snooze_cfg.get("snooze_seconds", default_snooze))
        except (TypeError, ValueError):
            snooze_s = _global_saturation = default_snooze
        sysmgr = getattr(dl, "system", None)
        ledger_raw = sysmgr.get_var("xcom_snooze") if sysmgr and hasattr(sysmgr, "get_var") else {}
        ledger = ledger_raw if isinstance(ledger_raw, dict) else {}
        last_raw = ledger.get(f"{mon}|{label}", 0)
        try:
            last_ts = float(last_raw)
        except (TypeError, ValueError):
            last_ts = 0.0
        if now - last_ts < max(0, _global_saturation):
            if sysmgr and hasattr(sysmgr, "set_var"):
                sysmgr.set_var("xcom_last_skip", {
                    "monitor": mon, "label": label, "ts": now,
                    "reason": "global-snooze", "remaining": int(max(0, _global_saturation - (now - last_ts)))
                })
            log.info("[xcom] skip %s %s due to snooze (remaining=%ss)", mon, label, int(max(0, _global_saturation - (now - last_ts))))
            continue

        subj, body, tts = _compose_text(r)

        voice_cfg: Dict[str, Any] = {}
        voice_needed = bool(channels.get("voice"))

        if voice_needed:
            voice_cfg, missing = _require_voice_provider(dl)
            if missing:
                log.error("[xcom] voice provider missing keys: %s", ", ".join(sorted(set(missing))))

                sysmgr = getattr(dl, "system", None)
                now = time.time()
                if sysmgr and hasattr(sysmgr, "set_var"):
                    sysmgr.set_var("xcom_last_error", {
                        "ts": now,
                        "monitor": mon,
                        "label": label,
                        "reason": "provider-missing",
                        "missing": sorted(set(missing)),
                    })

                try:
                    send_agg = _load_aggregator()
                    if callable(send_agg):
                        payload = {
                            "breach": True,
                            "monitor": mon,
                            "label": label,
                            "value": r.get("value"),
                            "threshold": {"op": r.get("thr_op"), "value": r.get("thr_value")},
                            "source": (r.get("meta") or {}).get("limit_source") or r.get("source"),
                            "cycle_id": r.get("cycle_id"),
                            "error": f"voice provider missing keys: {', '.join(sorted(set(missing)))}",
                        }
                        send_agg(mon, payload, {"system": True, "voice": False, "sms": False, "tts": False}, {"dl": dl})
                except Exception:
                    pass

                continue

        payload = {
            "breach": True,
            "monitor": mon,
            "label": label,
            "value": r.get("value"),
            "threshold": {"op": r.get("thr_op"), "value": r.get("thr_value")},
            "source": (r.get("meta") or {}).get("limit_source") or r.get("source"),
            "cycle_id": r.get("cycle_id"),
            "subject": subj,
            "body": body,
        }
        context = {"voice": {"tts": tts, "provider": voice_cfg}, "dl": dl}

        try:
            result = send(mon, payload, channels, context)
            out.append({"monitor": mon, "label": label, "channels": channels, "result": result})
            log.info("[xcom] dispatched %s %s -> %s", mon, label, json.dumps(channels))
            if sysmgr and hasattr(sysmgr, "set_var") and (isinstance(result, dict) or result):
                ledger = ledger or {}
                ledger[f"{mon}|{label}"] = now
                sysmgr.set_var("xcom_snooze", ledger)
        except Exception as e:
            log.error("[xcom] dispatch error for %s %s: %s", mon, label, e)
            if sysmgr and hasattr(sysmgr, "set_var"):
                sysmgr.set_var("xcom_last_error", {"monitor": mon, "label": label, "ts": now, "reason": f"dispatch-exception: {e}"})
            try:
                send(mon, {**payload, "error": str(e)}, {"system": True, "voice": False, "sms": False, "tts": False}, {"dl": dl})
            except Exception:
                pass

    log.info("[xcom] sent %d notifications (including error notifies)", len(out))
    return out
