"""
Dangerous but handy: delete all price rows for listed assets (so a good ingestor can re-fill cleanly).
Usage:
    python backend/scripts/wipe_prices_for_assets.py BTC ETH SOL
"""
import sys
from backend.data.data_locker import DataLocker
from backend.core.core_constants import MOTHER_DB_PATH

assets = sys.argv[1:] or []
if not assets:
    print("No assets provided.")
    raise SystemExit(2)

dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
cur = dl.db.get_cursor()
if not cur:
    print("No DB cursor.")
    raise SystemExit(2)

for a in assets:
    cur.execute("DELETE FROM prices WHERE asset_type = ?", (a,))
dl.db.commit()
print({"wiped_assets": assets})
