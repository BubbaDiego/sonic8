from typing import List
from ..models.types import NormalizedPosition
from ..models.mappers import to_normalized_position
from .position_source_solana import SolanaPositionSource

class PositionService:
    def __init__(self, source: SolanaPositionSource, writer):
        self.source = source
        self.writer = writer

    def refresh_wallet(self, wallet: str) -> List[NormalizedPosition]:
        raise NotImplementedError("Implement orchestration in Phase S-2: source -> map -> write")
