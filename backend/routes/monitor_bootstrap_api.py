# -*- coding: utf-8 -*-
"""
/api/monitor-settings/bootstrap
Return all monitor settings needed by Monitor Manager in one round-trip.

Payload shape:
{
  "liquidation": {...},
  "profit": {...},
  "market": {...},
  "sonic": {
    "interval_seconds": int,
    "enabled_sonic": bool,
    "enabled_liquid": bool,
    "enabled_profit": bool,
    "enabled_market": bool
  },
  "nearest": { "BTC": {"dist": 5.3, "side": "SHORT"}, ... }
}
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Depends

from backend.data.data_locker import DataLocker  # type: ignore
from backend.deps import get_app_locker

try:
    # public constants exist in the refreshed core
    from backend.core.monitor_core.sonic_monitor import MONITOR_NAME, DEFAULT_INTERVAL
except Exception:  # pragma: no cover - defensive
    MONITOR_NAME = "sonic_monitor"
    DEFAULT_INTERVAL = 60

router = APIRouter(prefix="/api/monitor-settings", tags=["monitor-settings"])


def _read_interval(dl: DataLocker) -> int:
    """Mirror of the helper in monitor_settings_api; tolerate missing tables."""
    cursor = getattr(getattr(dl, "db", None), "get_cursor", lambda: None)()
    if cursor is None:
        return DEFAULT_INTERVAL
    cursor.execute(
        "SELECT interval_seconds FROM monitor_heartbeat WHERE monitor_name = ?",
        (MONITOR_NAME,),
    )
    row = cursor.fetchone()
    try:
        return int(row[0]) if row and row[0] is not None else DEFAULT_INTERVAL
    except Exception:
        return DEFAULT_INTERVAL


def _nearest_liq(dl: DataLocker) -> Dict[str, Dict[str, Any]]:
    """Best-effort nearest liquidation distances by asset and side."""
    try:
        cur = dl.db.get_cursor()
        cur.execute(
            """
            WITH ranked AS (
                SELECT
                    asset_type,
                    position_type,
                    ABS(liquidation_distance) AS dist,
                    ROW_NUMBER() OVER (
                        PARTITION BY asset_type ORDER BY ABS(liquidation_distance)
                    ) AS rnk
                FROM positions
                WHERE status = 'ACTIVE'
            )
            SELECT asset_type, position_type, dist
              FROM ranked
             WHERE rnk = 1
            """
        )
        rows = cur.fetchall() or []
        return {
            r["asset_type"]: {"dist": round(float(r["dist"]), 2), "side": r["position_type"]}
            for r in rows
        }
    except Exception:
        return {}


@router.get("/bootstrap")
def get_bootstrap(dl: DataLocker = Depends(get_app_locker)) -> Dict[str, Any]:
    # Sonic flags + loop
    sonic_cfg = (dl.system.get_var("sonic_monitor") if getattr(dl, "system", None) else {}) or {}
    sonic = {
        "interval_seconds": _read_interval(dl),
        "enabled_sonic": bool(sonic_cfg.get("enabled_sonic", True)),
        "enabled_liquid": bool(sonic_cfg.get("enabled_liquid", True)),
        "enabled_profit": bool(sonic_cfg.get("enabled_profit", True)),
        "enabled_market": bool(sonic_cfg.get("enabled_market", True)),
    }

    # Liquidation config (persisted as a system var)
    liq = (dl.system.get_var("liquid_monitor") if getattr(dl, "system", None) else {}) or {}

    # Profit config (persisted as a system var via profit_settings_api)
    prof = (dl.system.get_var("profit_monitor") if getattr(dl, "system", None) else {}) or {}

    # Market config (may be empty in refreshed core, but safe to return)
    market = (dl.system.get_var("market_monitor") if getattr(dl, "system", None) else {}) or {}

    # Nearest liquidation distances
    nearest = _nearest_liq(dl)

    return {
        "liquidation": liq,
        "profit": prof,
        "market": market,
        "sonic": sonic,
        "nearest": nearest,
        # NOTE: we intentionally do NOT include /api/market/latest here;
        # the UI will lazy-load that after first paint to keep TTI low.
    }
