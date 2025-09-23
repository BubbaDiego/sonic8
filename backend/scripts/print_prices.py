"""Quick peek at the latest price rows the monitor consumes."""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List

from backend.core.core_constants import MOTHER_DB_PATH
from backend.data.data_locker import DataLocker


def latest_for(symbols: List[str]) -> Dict[str, Any]:
    dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    out: Dict[str, Any] = {}
    for symbol in symbols:
        latest = dl.get_latest_price(symbol) or {}
        out[symbol] = {
            "price": latest.get("current_price"),
            "ts": latest.get("ts") or latest.get("timestamp"),
            "raw": latest,
        }
    return out


if __name__ == "__main__":
    symbols = sys.argv[1:] or ["SPX", "BTC", "ETH", "SOL"]
    data = latest_for(symbols)
    print(json.dumps(data, indent=2))
