"""
GMX REST V2 client (Phase 1 stub).

Phase 2: implement calls to:
- /prices/tickers
- /prices/candles
- /tokens
- /markets, /markets/info
- signed prices endpoints
- APY/performance (optional)
"""
from typing import Dict, Any, List


class GmxRestClient:
    def __init__(self, hosts: List[str]):
        self.hosts = hosts

    def get_tickers(self) -> Dict[str, Any]:
        raise NotImplementedError("Phase 2")

    def get_markets_info(self) -> Dict[str, Any]:
        raise NotImplementedError("Phase 2")

    def get_tokens(self) -> Dict[str, Any]:
        raise NotImplementedError("Phase 2")
