"""Run the Market monitor once without HTTP (uses BaseMonitor pipeline).

Usage:
    python backend/scripts/run_market_monitor_local.py
"""
from __future__ import annotations

import json

from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.monitor_core.market_monitor import MarketMovementMonitor
from backend.data.data_locker import DataLocker


def main() -> None:
    # Ensure locker is initialized
    DataLocker.get_instance(str(MOTHER_DB_PATH))

    monitor = MarketMovementMonitor()
    status, result = monitor.run_cycle()
    payload = result if isinstance(result, dict) else {"result": str(result)}

    print("status:", status)
    print("result:", json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
