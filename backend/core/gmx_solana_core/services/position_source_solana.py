"""
Position source for GMX-Solana.

Phase S-1: stubbed interface used by PositionService. Phase S-2 will actually
query on-chain accounts via anchorpy/solana-py and map them to SolPosition.
"""
from typing import List
from ..models.types import SolPosition

class SolanaPositionSource:
    def __init__(self, rpc_client):
        self.rpc = rpc_client

    def list_open_positions(self, wallet: str, limit: int = 1000) -> List[SolPosition]:
        raise NotImplementedError("Implement in Phase S-2 using anchorpy/solana-py (IDLs + account parsing).")

    def fetch_position(self, position_key: str) -> SolPosition:
        raise NotImplementedError("Implement in Phase S-2 using anchorpy/solana-py.")
