#!/usr/bin/env python
"""
Check `_price_at()` output for past time deltas.
Usage:  python check_price_at.py
"""

from backend.data.data_locker import DataLocker
from backend.core.monitor_core.market_monitor import MarketMonitor
from datetime import timedelta

dl = DataLocker.get_instance()
mon = MarketMonitor(dl)

print("🔍 Checking historical prices for each asset...\n")

for asset in mon.ASSETS:
    print(f"=== {asset} ===")

    # Define deltas in seconds for 1h, 6h, 24h ago
    for hours in [1, 6, 24]:
        delta_sec = hours * 3600
        price = mon._price_at(asset, delta_sec)
        if price is None:
            print(f"  ❌ {hours}h ago: None")
        else:
            print(f"  ✅ {hours}h ago: {price:.4f}")

    print()

