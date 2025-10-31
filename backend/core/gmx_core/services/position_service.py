"""
PositionService orchestrates source → mapper → DL writer (Phase 1 stub).
"""
from typing import List
from ..models.types import GMXPosition, NormalizedPosition
from ..models.mappers import to_normalized_position


class PositionService:
    def __init__(self, position_source, positions_writer):
        self.source = position_source
        self.writer = positions_writer

    def refresh_wallet(self, wallet: str) -> List[NormalizedPosition]:
        # Phase 2: pull from source, map, write to DL
        raise NotImplementedError("Phase 2")
