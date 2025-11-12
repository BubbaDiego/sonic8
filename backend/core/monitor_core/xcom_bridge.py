from __future__ import annotations

import inspect
import json
import logging
import time
from typing import Any, Callable, Dict, Iterable, List, Tuple

log = logging.getLogger("sonic.engine")


# ---------- dispatcher adapter ----------
# We always expose a local "send" function with a uniform signature:
#     send(monitor: str, payload: dict, channels: dict, context: dict) -> Any
# It maps to the best available XCom dispatcher implementation at runtime.


def _bind_dispatcher() -> Tuple[Callable[[str, dict, dict, dict], Any], str]:
    """Bind dispatcher implementation with graceful fallbacks."""

    # 1) New aggregator path
    try:
        from backend.core.xcom_core.xcom_core import dispatch_notifications as _agg  # type: ignore

        try:
            import backend.core.xcom_core.dispatch as vmod  # type: ignore

            fn = getattr(vmod, "dispatch_voice_if_needed", None)
            if callable(fn):
                params = tuple(inspect.signature(fn).parameters.keys())
                if "monitor_name" not in params:
                    _orig = fn

                    def _patched(
                        *,
                        monitor_name=None,
                        payload=None,
                        channels=None,
                        context=None,
                        **kw,
                    ):
                        return _orig(payload=payload, channels=channels, context=context)

                    setattr(vmod, "dispatch_voice_if_needed", _patched)
                    log.info(
                        "[xcom] patched voice shim for aggregator compatibility (added monitor_name kw)"
                    )
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

    # 3) Voice-only shim; adapt to our uniform call
    try:
        from backend.core.xcom_core.dispatch import dispatch_voice_if_needed as _voice  # type: ignore

        def _send(mon: str, payload: dict, channels: dict, context: dict):
            return _voice(payload=payload, channels=channels, context=context)

        return _send, "voice-only"
    except Exception:
        pass

    # 4) Nothing available; no-op
    def _noop(mon: str, payload: dict, channels: dict, context: dict):
        return {"ok": False, "reason": "no-dispatcher"}

    return _noop, "noop"


# ---- helper: read dl_monitors rows for the latest cycle ----
def _iter_rows_from_mgr(mgr: Any) -> Iterable[Dict[str, Any]]:
    for meth in ("get_rows", "latest", "list", "all"):
        fn = getattr(mgr, meth, None)
        if callable(fn):
            try:
                got = fn()
                if isinstance(got, list):
                    for r in got:
                        if isinstance(r, dict):
                            yield r
                    return
            except Exception:
                pass
    for attr in ("rows", "items"):
        arr = getattr(mgr, attr, None)
        if isinstance(arr, list):
            for r in arr:
                if isinstance(r, dict):
                    yield r
            return


def _latest_dl_rows(dl) -> List[Dict[str, Any]]:
    mm = getattr(dl, "dl_monitors", None) or getattr(dl, "monitors", None)
    if not mm:
        return []
    return list(_iter_rows_from_mgr(mm))


# ---- helper: channel selection from JSON config ----
def _channels_for_monitor(cfg: Dict[str, Any], name: str) -> Dict[str, bool]:
    """
    name: 'liquid' | 'profit' | 'market' | 'price'
    Look in BOTH places and prefer the one that actually defines notifications:
      - <name>_monitor.notifications (if present)
      - <name>.notifications (fallback)
    """
    root1 = cfg.get(f"{name}_monitor") or {}
    root2 = cfg.get(name) or {}
    notif: Dict[str, Any] = {}
    if isinstance(root1, dict) and "notifications" in root1:
        notif = root1.get("notifications") or {}
    elif isinstance(root2, dict) and "notifications" in root2:
        notif = root2.get("notifications") or {}
    return {
        "system": bool(notif.get("system")),
        "voice": bool(notif.get("voice")),
        "sms": bool(notif.get("sms")),
        "tts": bool(notif.get("tts")),
    }


def _snooze_seconds(cfg: Dict[str, Any], name: str) -> int:
    root = cfg.get(f"{name}_monitor") or cfg.get(name) or {}
    # many configs only set snooze for profit; default others to 600s
    return int((root or {}).get("snooze_seconds", 600 if name != "profit" else 1200))


# ---- helper: DL.system-backed snooze ledger ----
def _should_fire_and_mark(dl, key: str, now: float, snooze_s: int) -> bool:
    """
    key: unique event key, e.g. 'liquid|SOL – Liq'
    Returns True iff enough time has passed; updates ledger when firing.
    """
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var") or not hasattr(sysmgr, "set_var"):
        return True  # no ledger available; allow fire

    ledger = sysmgr.get_var("xcom_snooze") or {}
    last_ts = float(ledger.get(key, 0))
    if (now - last_ts) < snooze_s:
        return False
    ledger[key] = now
    sysmgr.set_var("xcom_snooze", ledger)
    return True


# ---- helper: compose a friendly subject/body/tts from a monitor row ----
def _compose_text(row: Dict[str, Any]) -> Tuple[str, str, str]:
    mon = row.get("monitor", "")
    lab = row.get("label", "")
    val = row.get("value")
    thrv = row.get("thr_value")
    thro = row.get("thr_op") or ""
    src = (row.get("meta") or {}).get("limit_source") or row.get("source") or mon
    vtxt = f"{val:.2f}" if isinstance(val, (int, float)) else str(val or "-")
    ttxt = f"{thro} {thrv:.2f}" if isinstance(thrv, (int, float)) else "-"
    subj = f"[{mon.upper()}] {lab} BREACH"
    body = f"{lab}: value={vtxt} threshold={ttxt} source={src}"
    tts = f"{lab} breach. Value {vtxt} vs threshold {ttxt}."
    return subj, body, tts


# ---- main entry: dispatch BREACH rows from dl_monitors ----
def dispatch_breaches_from_dl(dl, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Reads dl_monitors latest rows, selects BREACH entries,
    resolves channels from JSON config, respects per-monitor snooze,
    and dispatches via xcom_core.dispatch_notifications(...).
    Returns a list of dispatch summaries.
    """
    send, mode = _bind_dispatcher()
    log.info("[xcom] dispatcher mode=%s", mode)

    if not isinstance(cfg, dict):
        cfg = {}

    rows = _latest_dl_rows(dl)
    log.info("[xcom] bridge starting; dl_rows=%d", len(rows))
    log.info("[xcom] channels(liquid)=%s", _channels_for_monitor(cfg, "liquid"))
    log.info("[xcom] channels(profit)=%s", _channels_for_monitor(cfg, "profit"))
    log.info(
        "[xcom] cfg.liquid has notifications? %s  | cfg.liquid_monitor has? %s",
        isinstance(cfg.get("liquid"), dict) and "notifications" in cfg.get("liquid"),
        isinstance(cfg.get("liquid_monitor"), dict)
        and "notifications" in cfg.get("liquid_monitor"),
    )
    if not rows:
        return []

    now = time.time()
    out: List[Dict[str, Any]] = []

    breaches = [r for r in rows if str(r.get("state", "")).upper() == "BREACH"]
    log.info("[xcom] breaches=%d", len(breaches))

    # process newest-first for determinism
    for r in breaches:

        mon = (r.get("monitor") or "").lower()
        if mon not in ("liquid", "profit", "market", "price"):
            continue

        channels = _channels_for_monitor(cfg, mon)
        if not any(channels.values()):
            continue  # nothing enabled

        # snooze / cooldown per monitor
        snooze_s = _snooze_seconds(cfg, mon)
        key = f"{mon}|{r.get('label', '?')}"
        if not _should_fire_and_mark(dl, key, now, snooze_s):
            continue

        subj, body, tts = _compose_text(r)
        payload = {
            "breach": True,
            "monitor": mon,
            "label": r.get("label"),
            "value": r.get("value"),
            "threshold": {"op": r.get("thr_op"), "value": r.get("thr_value")},
            "source": (r.get("meta") or {}).get("limit_source") or r.get("source"),
            "cycle_id": r.get("cycle_id"),
        }
        context = {
            "voice": {"tts": tts},
            "dl": dl,  # allow dispatcher to pull creds/providers
        }

        try:
            result = send(mon, payload, channels, context)
        except Exception as e:  # pragma: no cover - dispatch is external
            log.info("[xcom] dispatch error for %s %s: %s", mon, r.get("label"), e)
            continue

        summary = {
            "monitor": mon,
            "label": r.get("label"),
            "channels": {k: bool(v) for k, v in channels.items()},
            "result": result,
            "subject": subj,
            "body": body,
        }
        out.append(summary)
        log.info("[xcom] dispatched %s %s -> %s", mon, r.get("label"), json.dumps(channels))

    log.info("[xcom] sent %d notifications", len(out))

    return out


__all__ = ["dispatch_breaches_from_dl"]
