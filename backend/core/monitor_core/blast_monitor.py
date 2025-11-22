from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.core import config_oracle as ConfigOracle
from backend.data.data_locker import DataLocker
from backend.core.monitor_core.sonic.monitors import liquid_runner


def _safe_float(val: Any) -> Optional[float]:
    try:
        return float(val) if val is not None else None
    except Exception:
        return None


def _extract_travel_pct(pos: Dict[str, Any]) -> Optional[float]:
    for key in ("travel", "travel_pct", "travel_percent"):
        v = _safe_float(pos.get(key)) if isinstance(pos, dict) else None
        if v is not None:
            return v

    side = str(pos.get("side") or pos.get("position_side") or "").upper()
    entry = _safe_float(pos.get("entry") or pos.get("entry_price"))
    mark = _safe_float(pos.get("mark") or pos.get("mark_price") or pos.get("price"))
    liq_price = _safe_float(pos.get("liq_price") or pos.get("liquidation_price"))

    if entry is None or mark is None:
        return None

    if side == "SHORT":
        pct = (entry - mark) / entry * 100.0
        if liq_price is not None and mark >= liq_price:
            return -100.0
    else:
        pct = (mark - entry) / entry * 100.0
        if liq_price is not None and mark <= liq_price:
            return -100.0

    return pct if pct >= -100.0 else -100.0


def _liquid_snapshot(
    dl: DataLocker, thresholds: Dict[str, float]
) -> Dict[str, Dict[str, Any]]:
    positions = liquid_runner._open_positions(dl)
    snapshot: Dict[str, Dict[str, Any]] = {}

    for pos in positions:
        asset = liquid_runner._asset(pos)
        if not asset:
            continue

        distance = liquid_runner._liquid_distance_pct(pos)
        if distance is None:
            continue

        travel_pct = _extract_travel_pct(pos)
        sym = asset.upper()
        existing = snapshot.get(sym)
        if existing is None or distance < existing.get("distance", float("inf")):
            snapshot[sym] = {
                "distance": float(distance),
                "threshold": thresholds.get(sym),
                "travel_pct": travel_pct,
            }

    return snapshot


def run_blast_monitor(dl: DataLocker) -> List[Dict[str, Any]]:
    oracle = ConfigOracle.get_oracle()
    blast_cfg = oracle.get_blast_monitor_config()

    blast_radius_map = oracle.get_liquid_blast_map()
    thresholds = oracle.get_liquid_thresholds()

    snapshot = _liquid_snapshot(dl, thresholds)
    statuses: List[Dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for asset, info in snapshot.items():
        blast_radius = float(blast_radius_map.get(asset, 0) or 0)
        if blast_radius <= 0:
            continue

        ld = info.get("distance")
        if ld is None:
            continue

        encroached_pct = (blast_radius - float(ld)) / blast_radius * 100.0
        if encroached_pct < 0:
            encroached_pct = 0.0
        if encroached_pct > 100.0:
            encroached_pct = 100.0

        alert_pct = blast_cfg.get_alert_pct(asset, default=50.0)
        state = "BREACH" if encroached_pct >= alert_pct else "OK"

        meta = {
            "blast_radius": blast_radius,
            "liq_distance": float(ld),
            "liq_threshold": info.get("threshold"),
            "encroached_pct": encroached_pct,
            "alert_pct": alert_pct,
            "travel_pct": info.get("travel_pct"),
        }

        statuses.append(
            {
                "monitor": "blast",
                "label": f"{asset} – Blast",
                "asset": asset,
                "value": encroached_pct,
                "unit": "%",
                "threshold": {"op": ">=", "value": alert_pct, "unit": "%"},
                "state": state,
                "meta": meta,
                "source": "blast_monitor",
                "ts": now_iso,
            }
        )

    return statuses


def run_blast_monitors(ctx: Any) -> Dict[str, Any]:
    dl = None
    if isinstance(ctx, dict):
        dl = ctx.get("dl")
    if dl is None:
        dl = getattr(ctx, "dl", None)

    statuses = run_blast_monitor(dl) if dl is not None else []
    return {"source": "blast", "statuses": statuses}
