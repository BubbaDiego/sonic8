"""Debug endpoints for inspecting market monitor inputs and pure eval."""
from __future__ import annotations

import time
from typing import Any, Dict, List

from fastapi import APIRouter

from backend.core.core_constants import MOTHER_DB_PATH
from backend.data.data_locker import DataLocker

router = APIRouter(prefix="/debug/market", tags=["debug_market"])


def _get_cfg(dl: DataLocker) -> Dict[str, Any]:
    cfg: Dict[str, Any] = dl.system.get_var("market_monitor") if dl.system else {}
    if cfg is None:
        cfg = {}

    cfg.setdefault("thresholds", {})
    cfg.setdefault("anchors", {})
    cfg.setdefault("rearm_mode", "ladder")
    return cfg


def _get_latest_prices(dl: DataLocker, assets: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for asset in assets:
        latest = dl.get_latest_price(asset) or {}
        if latest:
            out[asset] = {
                "price": latest.get("current_price"),
                "ts": latest.get("ts") or latest.get("timestamp"),
                "source": latest.get("source") or "db",
            }
    return out


@router.get("/state")
def state() -> Dict[str, Any]:
    """Raw market monitor inputs for quick diagnosis: cfg + anchors + latest prices."""

    dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    cfg = _get_cfg(dl)
    assets = list(cfg["thresholds"].keys()) or ["SPX", "BTC", "ETH", "SOL"]
    prices = _get_latest_prices(dl, assets)
    now = int(time.time() * 1000)

    return {
        "now": now,
        "assets": assets,
        "cfg": cfg,
        "prices": prices,
        "notes": "Snooze/enable gating happens elsewhere; this is inputs-only.",
    }


@router.get("/eval")
def eval_inputs() -> Dict[str, Any]:
    """Pure function preview: computes deltas against anchors and indicates would-trigger flags."""

    dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    cfg = _get_cfg(dl)

    assets = list(cfg["thresholds"].keys()) or ["SPX", "BTC", "ETH", "SOL"]
    prices = _get_latest_prices(dl, assets)

    anchors = cfg.get("anchors", {})
    thresholds = cfg.get("thresholds", {})
    direction = cfg.get("direction", {})

    detail: Dict[str, Any] = {}
    for asset in assets:
        price = None if asset not in prices else prices[asset].get("price")
        anchor = anchors.get(asset)
        threshold = thresholds.get(asset)
        dirn = direction.get(asset) if isinstance(direction, dict) else None
        dirn = dirn or "Both"

        if price is None or anchor is None or threshold is None:
            detail[asset] = {
                "price": price,
                "anchor": anchor,
                "delta_abs": None,
                "threshold": threshold,
                "direction": dirn,
                "would_trigger": False,
                "reason": "missing price/anchor/threshold",
            }
            continue

        delta = price - anchor
        delta_abs = abs(delta)
        up = delta > 0
        dir_ok = (dirn == "Both") or (dirn == "Up" and up) or (dirn == "Down" and not up)
        would_trigger = bool(dir_ok and (delta_abs >= float(threshold)))

        detail[asset] = {
            "price": price,
            "anchor": anchor,
            "delta": delta,
            "delta_abs": delta_abs,
            "threshold": threshold,
            "direction": dirn,
            "dir_ok": dir_ok,
            "would_trigger": would_trigger,
        }

    return {
        "cfg_summary": {
            "rearm_mode": cfg.get("rearm_mode", "ladder"),
            "armed": cfg.get("armed", True),
        },
        "detail": detail,
    }
