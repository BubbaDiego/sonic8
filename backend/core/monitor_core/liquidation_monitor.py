# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging

log = logging.getLogger(__name__)

try:
    from backend.core.reporting_core.sonic_reporting.config_probe import discover_json_path, parse_json
except Exception:
    def discover_json_path(_): return None
    def parse_json(_): return {}, None, {}

_NEAREST_FROM_SUMMARY = None
try:
    from backend.core.monitor_core.summary_helpers import get_nearest_liquidation_distances as _N1  # type: ignore
    _NEAREST_FROM_SUMMARY = _N1
except Exception:
    pass

_NEAREST_FROM_REPORTING = None
try:
    from backend.core.reporting_core.sonic_reporting.evaluations_table import get_nearest_liquidation_distances as _N2  # type: ignore
    _NEAREST_FROM_REPORTING = _N2
except Exception:
    pass

from backend.data import dl_alerts

try:
    from backend.core.xcom_core.dispatch import dispatch_voice
except Exception:
    def dispatch_voice(*_a, **_k):  # type: ignore
        raise RuntimeError("XCOM dispatch not available")

def _is_num(x: Any) -> bool:
    try:
        float(x); return True
    except Exception:
        return False

def _load_cfg(default_json_path: Optional[str]) -> Dict:
    cfg = {}
    try:
        path = default_json_path or discover_json_path(None)
        if path:
            obj, err, meta = parse_json(path)
            if isinstance(obj, dict):
                cfg = obj
    except Exception as e:
        log.debug("liquidation_monitor: config parse failed", extra={"error": str(e)})
        cfg = {}
    return cfg

def _extract_thresholds(cfg: Dict) -> Dict[str, float]:
    t = cfg.get("liquid", {}).get("thresholds", {}) or {}
    if not t:
        t = cfg.get("liquid_monitor", {}).get("thresholds", {}) or {}
    out: Dict[str, float] = {}
    for k, v in (t or {}).items():
        try: out[str(k).upper()] = float(v)
        except Exception: pass
    return out

def _nearest_from_dl(dl: Any) -> Dict[str, float]:
    for key in ("liquid_nearest", "nearest_liquid_distances", "liquid_nearest_by_symbol"):
        v = getattr(dl, key, None)
        if isinstance(v, dict) and v:
            return {str(k).upper(): float(v[k]) for k in v if _is_num(v[k])}
    for key in ("sonic_summary", "summary", "enriched_summary"):
        d = getattr(dl, key, None)
        if isinstance(d, dict):
            liquid = d.get("liquid") or d.get("nearest") or {}
            if isinstance(liquid, dict):
                out: Dict[str, float] = {}
                for k, val in liquid.items():
                    if _is_num(val):
                        out[str(k).upper()] = float(val)
                    elif isinstance(val, dict):
                        for sub in ("distance", "nearest", "value"):
                            vv = val.get(sub)
                            if _is_num(vv): out[str(k).upper()] = float(vv); break
                if out: return out
    return {}

def _nearest_from_positions(dl: Any) -> Dict[str, float]:
    rows = []
    try:
        rows = dl.read_positions() if hasattr(dl, "read_positions") else getattr(dl, "positions", [])
        rows = rows or []
    except Exception:
        rows = []
    best: Dict[str, float] = {}
    for p in rows:
        try:
            sym = str(p.get("asset") or p.get("symbol") or "").upper()
            if not sym: continue
            cand = None
            for key in ("liq_distance", "liq_dist", "distance_to_liq", "nearest", "distance"):
                v = p.get(key)
                if _is_num(v):
                    cand = float(v); break
            if cand is None: continue
            if sym not in best or cand < best[sym]:
                best[sym] = cand
        except Exception:
            continue
    return best

def _get_nearest_map(dl: Any) -> Dict[str, float]:
    try:
        if _NEAREST_FROM_SUMMARY:
            d = _NEAREST_FROM_SUMMARY(dl)  # type: ignore
            if isinstance(d, dict) and d:
                return {str(k).upper(): float(d[k]) for k in d if _is_num(d[k])}
    except Exception: pass
    try:
        if _NEAREST_FROM_REPORTING:
            d = _NEAREST_FROM_REPORTING(dl)  # type: ignore
            if isinstance(d, dict) and d:
                return {str(k).upper(): float(d[k]) for k in d if _is_num(d[k])}
    except Exception: pass
    d = _nearest_from_dl(dl)
    if d: return d
    return _nearest_from_positions(dl)

class LiquidationMonitor:
    def __init__(self, default_json_path: Optional[str] = None):
        self.default_json_path = default_json_path

    def run(self, dl: Any) -> Dict[str, Any]:
        return _run_impl(dl, default_json_path=self.default_json_path)

    @staticmethod
    def run_static(dl: Any, default_json_path: Optional[str] = None) -> Dict[str, Any]:
        return _run_impl(dl, default_json_path=default_json_path)

def run(dl: Any, *, default_json_path: Optional[str] = None) -> Dict[str, Any]:
    return _run_impl(dl, default_json_path=default_json_path)

def _run_impl(dl: Any, *, default_json_path: Optional[str]) -> Dict[str, Any]:
    cfg = _load_cfg(default_json_path)
    thresholds = _extract_thresholds(cfg)
    nearest = _get_nearest_map(dl)

    dl_alerts.ensure_schema(dl)

    open_syms: List[str] = []
    for sym, thr in thresholds.items():
        val = nearest.get(sym)
        if _is_num(val) and float(val) <= float(thr):
            open_syms.append(sym)
            alert = dl_alerts.upsert_open(
                dl,
                kind="breach", monitor="liquid", symbol=sym,
                value=float(val), threshold=float(thr),
            )
            try:
                body = f"{sym} distance={float(val):.4f} threshold={float(thr):.4f}"
                payload = {
                    "breach": True,
                    "monitor": "liquid",
                    "label": sym,
                    "symbol": sym,
                    "subject": f"[LIQUID] {sym} BREACH",
                    "body": body,
                    "tts": f"{sym} breach. Distance {float(val):.2f} threshold {float(thr):.2f}.",
                    "summary": f"{sym} breach. Distance {float(val):.2f} threshold {float(thr):.2f}.",
                    "alert_id": alert["id"],
                }
                context = {
                    "dl": dl,
                    "voice": {"tts": payload["tts"]},
                    "alert": {
                        "source": "liquid",
                        "intent": "liquid-breach",
                        "symbol": sym,
                        "distance": float(val),
                        "threshold": float(thr),
                        "alert_id": alert["id"],
                        "twiml_url": getattr(dl, "twiml_url", None),
                    },
                }
                dispatch_voice(payload, {"voice": True}, context)
            except Exception as e:
                log.debug("liquidation_monitor: dispatch error", extra={"error": str(e), "symbol": sym})
        else:
            try:
                dl_alerts.resolve_open(dl, kind="breach", monitor="liquid", symbol=sym)
            except Exception as e:
                log.debug("liquidation_monitor: resolve error", extra={"error": str(e), "symbol": sym})

    return {"thresholds": thresholds, "nearest": nearest, "open": open_syms}
