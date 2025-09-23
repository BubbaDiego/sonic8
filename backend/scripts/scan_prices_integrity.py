"""
Scan the prices table for bad rows (e.g., TEXT in current_price).
Usage:
    python backend/scripts/scan_prices_integrity.py
"""
from backend.data.data_locker import DataLocker
from backend.core.core_constants import MOTHER_DB_PATH

dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
cur = dl.db.get_cursor()
bad = []
if cur:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prices'")
    if cur.fetchone():
        cur.execute(
            "SELECT id, asset_type, typeof(current_price) AS t_cp, current_price, "
            "typeof(previous_price) AS t_pp, previous_price, "
            "typeof(last_update_time) AS t_lu, last_update_time "
            "FROM prices ORDER BY asset_type, last_update_time DESC"
        )
        for r in cur.fetchall():
            is_bad = r["t_cp"] not in ("real", "integer")
            if is_bad:
                bad.append(dict(r))
        print(f"rows_scanned={len(bad)} (bad rows listed below)")
        for r in bad:
            print(r)
    else:
        print("No 'prices' table found.")
else:
    print("No DB cursor.")
