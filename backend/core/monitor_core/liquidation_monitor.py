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

try:
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:  # pragma: no cover - optional for CLI/tests
    DataLocker = None  # type: ignore[assignment]

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
    # Centralized config for liquidation thresholds (Oracle)
    from backend.core import config_oracle as ConfigOracle  # type: ignore
except Exception:  # pragma: no cover - defensive
    ConfigOracle = None  # type: ignore[assignment]

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

def _oracle_thresholds() -> Dict[str, float]:
    """
    Fetch liquidation thresholds from ConfigOracle if available.

    Returns:
        {SYMBOL: threshold_float}

    Symbols are normalized to upper-case. If Oracle is unavailable or
    misconfigured, returns an empty dict so the caller can fall back
    to legacy JSON config.
    """
    if ConfigOracle is None:
        return {}

    try:
        raw = ConfigOracle.get_liquid_thresholds() or {}
    except Exception as exc:  # pragma: no cover - defensive
        log.debug(
            "liquid_monitor: ConfigOracle.get_liquid_thresholds() failed",
            extra={"error": str(exc)},
        )
        return {}

    out: Dict[str, float] = {}
    for sym, val in raw.items():
        try:
            out[str(sym).upper()] = float(val)
        except Exception:
            # Ignore non-numeric values but keep others
            continue
    return out

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
    """
    Core execution for the standalone liquidation monitor.

    Thresholds are now Oracle-first:
      1) ConfigOracle.get_liquid_thresholds()
      2) legacy JSON config (sonic_monitor_config.json via _load_cfg)
    """
    # 1) Oracle-first thresholds
    thresholds = _oracle_thresholds()

    # 2) Legacy JSON fallback only if Oracle yields nothing
    if not thresholds:
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
                kind="breach",
                monitor="liquid",
                symbol=sym,
                value=float(val),
                threshold=float(thr),
            )
            try:
                body = f"{sym} distance={float(val):.4f} threshold={float(thr):.4f}"
                tts_text = (
                    f"{sym} liquidation breach. Distance {float(val):.2f} "
                    f"threshold {float(thr):.2f}."
                )
                payload = {
                    "breach": True,
                    "monitor": "liquid",
                    "label": sym,
                    "symbol": sym,
                    "subject": f"[LIQUID] {sym} BREACH",
                    "body": body,
                    "tts": tts_text,
                    # Summary feeds the voice message builder
                    "summary": tts_text,
                    "alert_id": alert["id"],
                    "threshold": {
                        "op": "<=",
                        "value": float(thr),
                    },
                }
                context = {
                    "dl": dl,
                    "voice": {
                        "tts": tts_text,
                    },
                    "alert": {
                        "source": "liquid",
                        "intent": "liquid-breach",
                        "symbol": sym,
                        "distance": float(val),
                        "threshold": float(thr),
                        "alert_id": alert["id"],
                    },
                }
                dispatch_voice(payload, {"voice": True}, context)
            except Exception as exc:
                log.debug(
                    "liquid_monitor: dispatch_voice failed",
                    extra={"error": str(exc), "symbol": sym},
                )
        else:
            try:
                dl_alerts.resolve_open(
                    dl, kind="breach", monitor="liquid", symbol=sym
                )
            except Exception as exc:
                log.debug(
                    "liquid_monitor: resolve_open failed",
                    extra={"error": str(exc), "symbol": sym},
                )

    return {"thresholds": thresholds, "nearest": nearest, "open": open_syms}


def _debug_thresholds(default_json_path: Optional[str]) -> None:
    """
    Debug utility: print out thresholds as seen by this monitor.

    Oracle thresholds are shown first, with a marker, then any legacy
    JSON thresholds (if Oracle had none).
    """
    th_oracle = _oracle_thresholds()
    if th_oracle:
        print("🧙 Oracle thresholds:")
        for sym, thr in sorted(th_oracle.items()):
            print(f"  {sym}: {thr}")
    else:
        print("🧙 Oracle thresholds: <none>")

    cfg = _load_cfg(default_json_path)
    th_legacy = _extract_thresholds(cfg)
    if th_legacy:
        print("📄 Legacy JSON thresholds:")
        for sym, thr in sorted(th_legacy.items()):
            print(f"  {sym}: {thr}")
    else:
        print("📄 Legacy JSON thresholds: <none>")


if __name__ == "__main__":  # pragma: no cover - CLI helper
    import argparse

    parser = argparse.ArgumentParser(description="Standalone liquidation monitor")
    parser.add_argument(
        "--dump-thresholds",
        action="store_true",
        help="Print Oracle + JSON thresholds and exit",
    )
    parser.add_argument(
        "--json-path",
        dest="json_path",
        default=None,
        help="Override default sonic_monitor_config.json path",
    )
    args = parser.parse_args()

    if args.dump_thresholds:
        _debug_thresholds(args.json_path)
    else:
        if DataLocker is None:
            raise RuntimeError("DataLocker import unavailable; cannot run monitor")
        dl = DataLocker.get_instance()
        result = _run_impl(dl, default_json_path=args.json_path)
        print(result)
