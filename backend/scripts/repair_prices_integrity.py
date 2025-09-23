"""
Repair common schema drift in 'prices':

If current_price is TEXT but previous_price is numeric, copy previous_price → current_price.

If both are non-numeric, NULL current_price so readers ignore the row.
Usage:
    python backend/scripts/repair_prices_integrity.py
"""
from backend.data.data_locker import DataLocker
from backend.core.core_constants import MOTHER_DB_PATH


def to_float(x):
    try:
        return float(x)
    except Exception:
        return None


dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
cur = dl.db.get_cursor()
fixed, nulled = 0, 0
if cur:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prices'")
    if cur.fetchone():
        cur.execute(
            "SELECT id, asset_type, current_price, previous_price, "
            "typeof(current_price) AS t_cp, typeof(previous_price) AS t_pp "
            "FROM prices"
        )
        rows = cur.fetchall()
        for r in rows:
            cp_ok = to_float(r["current_price"])
            if cp_ok is not None:
                continue
            pp_ok = to_float(r["previous_price"])
            if pp_ok is not None:
                cur.execute(
                    "UPDATE prices SET current_price = ? WHERE id = ?",
                    (pp_ok, r["id"]),
                )
                fixed += 1
            else:
                cur.execute(
                    "UPDATE prices SET current_price = NULL WHERE id = ?",
                    (r["id"],),
                )
                nulled += 1
        dl.db.commit()
        print({"fixed_from_previous": fixed, "nulled": nulled, "scanned": len(rows)})
    else:
        print("No 'prices' table found.")
else:
    print("No DB cursor.")
