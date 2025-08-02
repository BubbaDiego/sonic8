#!/usr/bin/env python
"""
Correct Backfill monitor_ledger using exact historical prices from DB.
"""

import sys, json
from datetime import datetime, timedelta, timezone
from backend.data.data_locker import DataLocker
from backend.core.core_constants import MOTHER_DB_PATH

LOOKBACK_HOURS = int(sys.argv[1]) if len(sys.argv) > 1 else 48
ASSETS = ["BTC", "SOL", "ETH", "SPX"]

dl = DataLocker(str(MOTHER_DB_PATH))
cur = dl.db.get_cursor()

end = datetime.now(timezone.utc)
start = end - timedelta(hours=LOOKBACK_HOURS)

def get_price_at(asset, ts):
    cur.execute(
        """
        SELECT current_price FROM prices
        WHERE asset_type = ? AND CAST(last_update_time AS REAL) <= ?
        ORDER BY CAST(last_update_time AS REAL) DESC LIMIT 1
        """,
        (asset, ts.timestamp()),
    )
    row = cur.fetchone()
    return row["current_price"] if row else None

print(f"⏳ Correctly backfilling monitor_ledger for {LOOKBACK_HOURS} hours using DB prices...")

ts = start
rows_inserted = 0
while ts <= end:
    details = []

    for asset in ASSETS:
        windows_data = {}
        cur_price = get_price_at(asset, ts)

        if cur_price is None:
            continue  # skip asset if no price at current timestamp

        for win, hours_back in [("1h", 1), ("6h", 6), ("24h", 24)]:
            past_ts = ts - timedelta(hours=hours_back)
            prev_price = get_price_at(asset, past_ts)

            if prev_price is None or prev_price == 0:
                pct_move = 0.0
            else:
                pct_move = (cur_price - prev_price) / prev_price * 100.0

            windows_data[win] = {
                "pct_move": round(pct_move, 4),
                "threshold": None,  # Adjust threshold logic if needed
                "trigger": None     # Adjust trigger logic if needed
            }

        details.append({"asset": asset, "windows": windows_data})

    payload = {"triggered": False, "details": details}

    cur.execute("""
        INSERT INTO monitor_ledger (monitor_name, status, metadata, created_at, timestamp)
        VALUES (?, 'Success', ?, ?, ?)
    """, ("market_monitor", json.dumps(payload), ts.isoformat(), ts.isoformat()))

    rows_inserted += 1
    ts += timedelta(hours=1)

dl.db.commit()

print(f"✅ Done. Inserted {rows_inserted} rows into monitor_ledger correctly.")
