#!/usr/bin/env python3
"""Seed portfolio history with a few sample snapshots.

This helper inserts three portfolio snapshot records so that the
PerformanceGraphCard has data to render. Run it once after
initializing the database.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
from typing import Sequence

from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import configure_console_log
from backend.data.data_locker import DataLocker


def seed_history(locker: DataLocker) -> None:
    """Insert three sample snapshots into ``positions_totals_history``."""
    now = datetime.now()
    snapshots = []
    for i in range(3):
        ts = now - timedelta(days=2 - i)
        snapshots.append(
            {
                "id": str(uuid4()),
                "snapshot_time": ts.isoformat(),
                "total_size": 1.0 + i,
                "total_value": 1000.0 + i * 50.0,
                "total_collateral": 500.0 + i * 25.0,
                "avg_leverage": 1.5,
                "avg_travel_percent": 0.1,
                "avg_heat_index": 0.2,
                "market_average_sp500": 4300.0 + i * 10.0,
            }
        )

    for snap in snapshots:
        locker.add_portfolio_entry(snap)

    print(f"\u2705 Inserted {len(snapshots)} portfolio snapshots")


def main(argv: Sequence[str] | None = None) -> int:
    configure_console_log()
    locker = DataLocker(str(MOTHER_DB_PATH))
    seed_history(locker)
    locker.close()
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution
    raise SystemExit(main())
