from typing import List
from ..models.types import SolPosition

class SolanaPositionSource:
    def __init__(self, rpc_client):
        self.rpc = rpc_client

    def list_open_positions(self, wallet: str, limit: int = 1000) -> List[SolPosition]:
        # S-2.1 will use IDL + memcmp filters to fetch wallet positions
        raise NotImplementedError("Positions decode lands in Phase S-2.1 (Anchor IDL).")

    def fetch_position(self, position_key: str) -> SolPosition:
        raise NotImplementedError("Positions decode lands in Phase S-2.1 (Anchor IDL).")
