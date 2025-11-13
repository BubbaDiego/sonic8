from __future__ import annotations

import logging
import time
from importlib import import_module
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("sonic.engine")


# --------- Provider discovery (NO shim imports) ---------
def _load_aggregator():
    """Load the multi-channel aggregator directly from xcom_core.xcom_core."""
    try:
        mod = import_module("backend.core.xcom_core.xcom_core")
        fn = getattr(mod, "dispatch_notifications", None)
        if callable(fn):
            return fn
    except Exception as exc:
        log.info("[xcom] aggregator import failed: %s", exc)
    return None


def _load_voice_sender():
    """Load the low-level voice sender (not the shim)."""
    try:
        mod = import_module("backend.core.xcom_core.dispatch")
        for name in ("voice_call", "send_voice", "dispatch_voice", "dispatch_voice_if_needed"):
            fn = getattr(mod, name, None)
            if callable(fn):
                return fn
    except Exception as exc:
        log.info("[xcom] voice sender import failed: %s", exc)
    return None


# --------- Config helpers ---------
def _channels_for_monitor(cfg: Dict[str, Any], name: str) -> Dict[str, bool]:
    channels = {"system": False, "voice": False, "sms": False, "tts": False}
    for key in (f"{name}_monitor", name):
        root = cfg.get(key)
        if not isinstance(root, dict):
            continue
        notif = root.get("notifications")
        if not isinstance(notif, dict):
            continue
        for channel in channels:
            if channel in notif:
                channels[channel] = bool(notif[channel])
    return channels


def _snooze_seconds(cfg: Dict[str, Any], mon: str) -> int:
    for key in (f"{mon}_monitor", mon):
        root = cfg.get(key)
        if not isinstance(root, dict):
            continue
        raw = root.get("snooze_seconds")
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return 1200 if mon == "profit" else 600


def _cfg_path_hint(ctx: Dict[str, Any]) -> str:
    path = ctx.get("cfg_path_hint")
    return str(path) if path else "<unknown>"


# --------- DL helpers ---------
def _latest_dl_rows(dl) -> List[Dict[str, Any]]:
    mgr = getattr(dl, "dl_monitors", None) or getattr(dl, "monitors", None)
    if not mgr:
        return []

    for attr in ("get_rows", "latest", "list", "all"):
        fn = getattr(mgr, attr, None)
        if callable(fn):
            try:
                rows = fn()
                if isinstance(rows, list):
                    return rows
            except Exception as exc:
                log.info("[xcom] dl_monitors.%s error: %s", attr, exc)
    rows = getattr(mgr, "rows", None) or getattr(mgr, "items", None)
    return rows if isinstance(rows, list) else []


def _snooze_gate(dl, key: str, seconds: int) -> bool:
    """Return True if we should fire (i.e., snooze window has elapsed)."""
    if seconds <= 0:
        return True

    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var") or not hasattr(sysmgr, "set_var"):
        return True

    try:
        ledger = sysmgr.get_var("xcom_snooze") or {}
    except Exception as exc:
        log.info("[xcom] snooze ledger load failed: %s", exc)
        return True

    if not isinstance(ledger, dict):
        ledger = {}

    now = time.time()
    try:
        last = float(ledger.get(key, 0.0))
    except (TypeError, ValueError):
        last = 0.0

    if now - last < float(seconds):
        return False

    ledger[key] = now
    try:
        sysmgr.set_var("xcom_snooze", ledger)
    except Exception as exc:
        log.info("[xcom] snooze ledger persist failed: %s", exc)
    return True


# --------- Formatting helpers ---------
def _fmt(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return str(value) if value is not None else "-"


def _compose_text(row: Dict[str, Any]) -> Tuple[str, str, str]:
    monitor = (row.get("monitor") or "").upper()
    label = row.get("label") or ""
    value = _fmt(row.get("value"))
    thr_val = _fmt(row.get("thr_value"))
    thr_op = row.get("thr_op") or ""
    source = (row.get("meta") or {}).get("limit_source") or row.get("source") or ""

    subject = f"[{monitor}] {label} BREACH" if monitor else f"{label} BREACH"
    body = f"{label}: value={value} threshold={thr_op} {thr_val} (src={source})"
    tts = f"{label} breach. Value {value} versus threshold {thr_op} {thr_val}."
    return subject, body, tts


# --------- Main bridge (no shim) ---------
def dispatch_breaches_from_dl(
    dl,
    cfg: Dict[str, Any],
    *,
    ctx: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    ctx = ctx or {}
    log.info("[xcom] cfg path: %s", _cfg_path_hint(ctx))

    aggregator = _load_aggregator()
    voice_fn = _load_voice_sender()
    if not aggregator and not voice_fn:
        log.info("[xcom] no xcom providers available")
        return []

    rows = _latest_dl_rows(dl)
    log.info("[xcom] dl rows: %d", len(rows))
    breaches = [row for row in rows if str(row.get("state", "")).upper() == "BREACH"]
    if not breaches:
        log.info("[xcom] no BREACH rows")
        return []

    sent: List[Dict[str, Any]] = []
    for row in breaches:
        monitor = (row.get("monitor") or "").lower()
        if not monitor:
            log.info("[xcom] skip row with missing monitor: %s", row)
            continue

        channels = _channels_for_monitor(cfg, monitor)
        if not any(channels.values()):
            log.info("[xcom] %s:%s no channels enabled; skip", monitor, row.get("label"))
            continue

        snooze_window = _snooze_seconds(cfg, monitor)
        key = f"{monitor}|{row.get('label', '')}"
        if not _snooze_gate(dl, key, snooze_window):
            log.info("[xcom] snoozed %s for %ss", key, snooze_window)
            continue

        subject, body, tts = _compose_text(row)
        payload = {
            "breach": True,
            "monitor": monitor,
            "label": row.get("label"),
            "value": row.get("value"),
            "threshold": {"op": row.get("thr_op"), "value": row.get("thr_value")},
            "source": (row.get("meta") or {}).get("limit_source") or row.get("source"),
            "subject": subject,
            "body": body,
        }
        context = {"subject": subject, "body": body, "source": payload["source"], "tts": tts}

        entry: Dict[str, Any] = {"monitor": monitor, "label": row.get("label"), "channels": dict(channels)}

        if aggregator:
            channel_map = {
                "system": bool(channels.get("system")),
                "sms": bool(channels.get("sms")),
                "tts": bool(channels.get("tts")),
                "voice": False,
            }
            try:
                agg_result = aggregator(monitor, payload, channel_map, context)
                entry["aggregator_result"] = agg_result
                log.info("[xcom] %s:%s non-voice -> %s", monitor, row.get("label"), agg_result)
            except Exception as exc:
                log.info("[xcom] %s:%s non-voice error: %s", monitor, row.get("label"), exc)

        if channels.get("voice") and voice_fn:
            reason_ctx = {
                "subject": subject,
                "body": body,
                "source": monitor,
                "label": row.get("label"),
                "intent": f"{monitor}-breach",
                "tts": tts,
            }
            try:
                try:
                    voice_fn(
                        dl,
                        breach=True,
                        to_number=None,
                        from_number=None,
                        reason_ctx=reason_ctx,
                    )
                    entry["voice_result"] = True
                    log.info("[xcom] %s:%s voice -> OK", monitor, row.get("label"))
                except TypeError:
                    try:
                        voice_fn(monitor, row.get("label"), body)
                        entry["voice_result"] = True
                        log.info(
                            "[xcom] %s:%s voice -> OK (monitor,label,text)",
                            monitor,
                            row.get("label"),
                        )
                    except TypeError:
                        voice_fn({"voice": True}, body)
                        entry["voice_result"] = True
                        log.info(
                            "[xcom] %s:%s voice -> OK (channels,text)",
                            monitor,
                            row.get("label"),
                        )
            except Exception as exc:
                entry["voice_result"] = False
                log.info("[xcom] %s:%s voice error: %s", monitor, row.get("label"), exc)

        sent.append(entry)

    log.info("[xcom] sent %d notifications", len(sent))
    return sent
