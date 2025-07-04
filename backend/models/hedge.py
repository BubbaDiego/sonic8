"""Data model representing a hedge grouping of positions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class Hedge:
    """Represents a calculated hedge comprised of multiple positions."""

    id: str
    positions: List[str] = field(default_factory=list)
    total_long_size: float = 0.0
    total_short_size: float = 0.0
    long_heat_index: float = 0.0
    short_heat_index: float = 0.0
    total_heat_index: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: str = ""


__all__ = ["Hedge"]
