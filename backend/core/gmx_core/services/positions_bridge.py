"""
PositionsBridge (Phase 1 stub).

Bridges GMXPosition objects → NormalizedPosition → DL write.
"""
from typing import List
from ..models.types import GMXPosition, NormalizedPosition
from ..models.mappers import to_normalized_position


class PositionsBridge:
    def map_batch(self, gmx_positions: List[GMXPosition]) -> List[NormalizedPosition]:
        return [to_normalized_position(p) for p in gmx_positions]
