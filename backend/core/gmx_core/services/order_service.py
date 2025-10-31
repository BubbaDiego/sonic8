"""
OrderService (Phase 1 stub).

Phase 6 (optional): headless order creation/cancel guarded by feature flags.
"""
from typing import Dict, Any


class OrderService:
    def __init__(self, router_client):
        self.router = router_client

    def create_market_increase(self, params: Dict[str, Any]) -> str:
        raise NotImplementedError("Phase 6")
