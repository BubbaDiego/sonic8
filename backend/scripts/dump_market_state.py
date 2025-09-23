"""Offline snapshot of market config + anchors + prices as seen by the app."""
from __future__ import annotations

import json
from typing import Any, Dict, List

from backend.core.core_constants import MOTHER_DB_PATH
from backend.data.data_locker import DataLocker


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


def main() -> None:
    dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    cfg = _get_cfg(dl)
    assets = list(cfg["thresholds"].keys()) or ["SPX", "BTC", "ETH", "SOL"]
    prices = _get_latest_prices(dl, assets)

    snapshot = {
        "cfg": cfg,
        "assets": assets,
        "prices": prices,
    }
    print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()
