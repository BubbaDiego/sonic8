"""Inspect recent price rows from the ``prices`` table."""

import json
import sys

from backend.core.core_constants import MOTHER_DB_PATH
from backend.data.data_locker import DataLocker


def main() -> None:
    """Print recent rows for selected assets showing SQLite types."""

    symbols = sys.argv[1:] or ["BTC", "ETH", "SOL", "SPX"]
    dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    cur = dl.db.get_cursor()
    if cur is None:
        print("{}")
        return

    result: dict[str, list[dict[str, object]]] = {}
    for symbol in symbols:
        cur.execute(
            "SELECT asset_type, "
            "typeof(current_price) AS t_cp, current_price, "
            "typeof(previous_price) AS t_pp, previous_price, "
            "typeof(last_update_time) AS t_lut, last_update_time, "
            "typeof(previous_update_time) AS t_plut, previous_update_time, "
            "source "
            "FROM prices WHERE asset_type = ? "
            "ORDER BY last_update_time DESC LIMIT 3",
            (symbol,),
        )
        rows = cur.fetchall() or []
        result[symbol] = [dict(row) for row in rows]

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
