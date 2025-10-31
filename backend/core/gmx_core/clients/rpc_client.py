"""
EVM RPC + WebSocket client (Phase 1 stub).

Phase 2:
- implement WS subscription to EventEmitter logs
- lightweight ABI calls for Reader/DataStore views
- retry/backoff + provider failover
"""
from typing import Optional


class EvmRpcClient:
    def __init__(self, http_url: str, ws_url: Optional[str] = None):
        self.http_url = http_url
        self.ws_url = ws_url

    def connect(self) -> None:
        # Phase 2: open WS session if provided, validate chain id via eth_chainId
        return None

    def close(self) -> None:
        # Phase 2: close WS
        return None
