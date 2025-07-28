#!/usr/bin/env python3
"""Seed Liquidation Distance and Profit alert thresholds.

This script inserts default thresholds via ``DLThresholdManager``. It mirrors
running the following API requests:

```
curl -X POST http://localhost:5000/alert_thresholds/ \
     -H 'Content-Type: application/json' \
     -d '{"alert_type":"LiquidationDistance","alert_class":"Position","metric_key":"liquidation_distance","condition":"BELOW","low":5,"medium":3,"high":1}'

curl -X POST http://localhost:5000/alert_thresholds/ \
     -H 'Content-Type: application/json' \
     -d '{"alert_type":"Profit","alert_class":"Portfolio","metric_key":"pnl_after_fees_usd","condition":"ABOVE","low":10,"medium":25,"high":50}'
```
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from typing import Sequence

from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import configure_console_log
from backend.data.data_locker import DataLocker
from backend.data.dl_thresholds import DLThresholdManager
from backend.models.alert_thresholds import AlertThreshold


def seed_thresholds(locker: DataLocker) -> None:
    """Insert default Liquidation Distance and Profit thresholds."""
    mgr = DLThresholdManager(locker.db)
    now = datetime.now(timezone.utc).isoformat()
    thresholds = [
        AlertThreshold(
            id=str(uuid4()),
            alert_type="LiquidationDistance",
            alert_class="Position",
            metric_key="liquidation_distance",
            condition="BELOW",
            low=5.0,
            medium=3.0,
            high=1.0,
            last_modified=now,
        ),
        AlertThreshold(
            id=str(uuid4()),
            alert_type="Profit",
            alert_class="Portfolio",
            metric_key="pnl_after_fees_usd",
            condition="ABOVE",
            low=10.0,
            medium=25.0,
            high=50.0,
            last_modified=now,
        ),
    ]
    for th in thresholds:
        mgr.insert(th)

    print(f"\u2705 Inserted {len(thresholds)} alert thresholds")


def main(argv: Sequence[str] | None = None) -> int:
    configure_console_log()
    locker = DataLocker(str(MOTHER_DB_PATH))
    seed_thresholds(locker)
    locker.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
