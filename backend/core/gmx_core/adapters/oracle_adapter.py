"""
Oracle adapter (Phase 1 stub).

Phase 2:
- unify REST tickers + Reader prices
- return a simple structure for mark/entry/liq funding lookups
"""
from typing import Dict, Any


class OracleAdapter:
    def __init__(self, rest_client, reader_client):
        self.rest = rest_client
        self.reader = reader_client

    def mark_price(self, symbol_or_market: str) -> Dict[str, Any]:
        raise NotImplementedError("Phase 2")
