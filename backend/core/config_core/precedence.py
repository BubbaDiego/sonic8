from __future__ import annotations
from enum import Enum, auto
from typing import List

class PrecedencePolicy(Enum):
    JSON_FIRST = auto()  # JSON > DB > ENV  (JSON wins)
    DB_FIRST   = auto()  # DB > JSON > ENV  (DB wins)

    def order(self) -> List[str]:
        """
        Merge order (earlier = lower priority, later = higher priority).
        We always start from defaults; then apply these layers in order.
        """
        if self is PrecedencePolicy.JSON_FIRST:
            return ["env", "db", "json"]   # later wins → JSON highest
        else:
            return ["env", "json", "db"]   # later wins → DB highest
