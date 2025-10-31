"""
FundingService (Phase 1 stub).

Phase 4:
- compute funding/borrow over intervals
- persist snapshots to DL
"""
from typing import Any


class FundingService:
    def __init__(self, oracle_adapter):
        self.oracle = oracle_adapter

    def snapshot(self) -> Any:
        raise NotImplementedError("Phase 4")
