"""
GMX ExchangeRouter wrapper (Phase 1 stub).

Phase 6 (optional):
- compose Router.multicall(sendWnt, sendTokens, createOrder)
- encode CreateOrderParams
- apply execution fee buffers
"""
from typing import Any, Dict


class GmxRouterClient:
    def __init__(self, rpc_http: str, router_addr: str, order_vault_addr: str):
        self.rpc_http = rpc_http
        self.router_addr = router_addr
        self.order_vault_addr = order_vault_addr

    def build_market_increase(self, params: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Phase 6")
