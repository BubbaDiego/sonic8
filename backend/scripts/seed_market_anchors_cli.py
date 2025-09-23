"""Seed/reset market anchors from latest prices (offline).

Usage:
    python backend/scripts/seed_market_anchors_cli.py
"""
from __future__ import annotations

import json

from backend.core.core_constants import MOTHER_DB_PATH
from backend.data.data_locker import DataLocker


def main() -> None:
    dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    cfg = (dl.system.get_var("market_monitor") or {}) if dl.system else {}
    thresholds = cfg.get("thresholds") or {}
    assets = list(thresholds.keys()) or ["SPX", "BTC", "ETH", "SOL"]

    anchors = {}
    for asset in assets:
        price = dl.get_latest_price(asset) or {}
        if price and price.get("current_price") is not None:
            anchors[asset] = float(price["current_price"])

    cfg["anchors"] = anchors
    cfg["armed"] = True

    if dl.system:
        dl.system.set_var("market_monitor", cfg)

    print(json.dumps({"anchors": anchors, "armed": True}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
