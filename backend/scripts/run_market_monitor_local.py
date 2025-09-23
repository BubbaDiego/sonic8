"""Run the Market monitor once (offline) and pretty-print the result.

Usage:
    python backend/scripts/run_market_monitor_local.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on ``sys.path`` when running from ``backend/scripts``.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.monitor_core.market_monitor import MarketMovementMonitor
from backend.data.data_locker import DataLocker


def main() -> None:
    """Execute :class:`MarketMovementMonitor` once and log the result."""

    # Ensure the DataLocker singleton is initialised before running the monitor.
    DataLocker.get_instance(str(MOTHER_DB_PATH))

    monitor = MarketMovementMonitor()
    result = monitor.run_cycle()  # BaseMonitor.run_cycle() returns a dict or None

    if result is None:
        print("status: Error")
        print(json.dumps({"error": "run_cycle returned None"}, indent=2, sort_keys=True))
        return

    status = "Success"
    if isinstance(result, dict):
        status_field = str(result.get("status") or "").lower()
        if status_field and status_field != "success":
            status = "Error"
    else:
        result = {"result": str(result)}

    print("status:", status)
    print("result:", json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
