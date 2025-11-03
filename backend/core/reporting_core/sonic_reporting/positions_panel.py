"""Console positions panel shim.

This bridges the legacy ``positions_snapshot`` implementation with the new
``positions_panel`` module name so the sequencer can import it directly.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .positions_snapshot import (
    _print_positions_table,
    _resolve_positions,
    _row_from_position,
)

__all__ = ["render"]


def render(dl: Any, csum: Dict[str, Any], default_json_path: Optional[str] = None) -> None:
    """Render the positions table using the snapshot helpers."""
    rows_raw = _resolve_positions()
    rows = [_row_from_position(p) for p in rows_raw]
    _print_positions_table(rows)
