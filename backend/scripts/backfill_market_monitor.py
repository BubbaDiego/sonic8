#!/usr/bin/env python
"""
Back-fill market_monitor ledger (with timestamp fix)
----------------------------------------------------

Default look-back period: 24 hours. Can be overridden by CLI argument.

Usage:
  python backend/scripts/backfill_market_monitor.py [hours]

Example:
  python backend/scripts/backfill_market_monitor.py 48
"""

import sys, json, os
from datetime import datetime, timedelta, timezone

REPO_ROOT = os.path.abspath(os.path.join(__file__, "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.data.data_locker import DataLocker
from backend.core.monitor_core.market_monitor import MarketMonitor

LOOKBACK_HOURS: int = int(sys.argv[1]) if len(sys.argv) > 1 else 24
STEP_HOURS: int = 1

def main(hours_back: int = LOOKBACK_HOURS, step: int = STEP_HOURS):
    dl = DataLocker.get_instance()
    mon = MarketMonitor(dl)

    now_utc = datetime.now(timezone.utc)
    cur = dl.db.get_cursor()

    rows_written = 0
    for h in range(hours_back, 0, -step):
        ts_end = now_utc - timedelta(hours=h)
        delta_sec = int((now_utc - ts_end).total_seconds())

        cfg = mon._cfg()
        results, flagged = [], False

        for asset in mon.ASSETS:
            windows_data = {}
            cur_price = mon._price_at(asset, delta_sec)

            for win, secs in mon.WINDOWS.items():
                prev_price = mon._price_at(asset, delta_sec + secs) or cur_price
                pct = 0.0 if prev_price == 0 else (cur_price - prev_price) / prev_price * 100.0
                thr = cfg["thresholds"][asset][win]
                hit = abs(pct) >= thr
                windows_data[win] = {
                    "pct_move": round(pct, 4),
                    "threshold": thr,
                    "trigger": hit,
                }
                flagged |= hit

            results.append({"asset": asset, "windows": windows_data})

        payload = {"triggered": flagged, "details": results}

        # explicitly set timestamp
        cur.execute(
            """
            INSERT INTO monitor_ledger 
            (monitor_name, status, metadata, created_at, timestamp)
            VALUES (?, 'Success', ?, ?, ?)
            """,
            (mon.name, json.dumps(payload), ts_end.isoformat(), ts_end.isoformat()),
        )
        rows_written += 1

    dl.db.commit()
    print(f"✅  Back-filled {rows_written} rows for '{mon.name}' "
          f"({hours_back} h look-back).")

if __name__ == "__main__":
    main()
