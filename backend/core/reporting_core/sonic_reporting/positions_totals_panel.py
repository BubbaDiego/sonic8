"""Console positions totals panel shim."""
from __future__ import annotations

from typing import Any, Dict, Optional

from backend.core.monitor_core.positions_totals_printer import (
    compute_weighted_totals,
    print_positions_totals_line,
)

from .positions_snapshot import _resolve_positions, _row_from_position

__all__ = ["render"]

# Widths that mirror the main positions table layout.
WIDTHS = {
    "a": 5,
    "asset": 5,
    "s": 6,
    "side": 6,
    "v": 10,
    "value": 10,
    "p": 10,
    "pnl": 10,
    "l": 7,
    "lev": 7,
    "liq": 8,
    "t": 8,
    "travel": 8,
}


def render(dl: Any, csum: Dict[str, Any], default_json_path: Optional[str] = None) -> None:
    """Render the totals line underneath the positions panel."""
    rows_raw = _resolve_positions()
    rows = [_row_from_position(p) for p in rows_raw]
    totals = compute_weighted_totals(rows)
    print_positions_totals_line(totals, WIDTHS)
