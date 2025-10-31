"""
DL writer for positions (Phase 1 stub).

Phase 2:
- write normalized positions to Data Locker using existing DL APIs
"""
from typing import List
from ..models.types import NormalizedPosition

# Avoid hard-coupling here; import lazily in Phase 2 to match your DL API.
# from backend.data.data_locker import DataLocker


def write_positions(dl, positions: List[NormalizedPosition]) -> None:
    """
    Persist positions in the same schema your monitors/reporting already consume.
    'dl' may be a DataLocker instance or module facade used in your codebase.
    """
    raise NotImplementedError("Phase 2")
