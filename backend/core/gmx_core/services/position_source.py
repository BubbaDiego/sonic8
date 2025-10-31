"""
GMX Position Source (Phase 1 shape).

This is the surface that Position Sync Service will call in Phase 2:
- list_open_positions(wallet)
- fetch_position(position_key)
"""
from typing import List
from ..models.types import GMXPosition


class GMXPositionSource:
    def __init__(self, chain_key: str, config: dict):
        self.chain_key = chain_key
        self.config = config

    def list_open_positions(self, wallet: str) -> List[GMXPosition]:
        raise NotImplementedError("Phase 2")

    def fetch_position(self, position_key: str) -> GMXPosition:
        raise NotImplementedError("Phase 2")
