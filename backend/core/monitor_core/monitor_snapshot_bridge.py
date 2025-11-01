from __future__ import annotations

from typing import Dict, Any
from backend.core.reporting_core.sonic_reporting.positions_snapshot_v1 import (
    build_positions_snapshot,
)


def get_positions_rows_and_totals() -> Dict[str, Any]:
    """
    Bridge for the TUI monitor: returns {"rows": [...], "totals": {...}}
    so the monitor's table render can be a pure view.
    """
    snap = build_positions_snapshot()
    return {"rows": snap.get("rows", []), "totals": snap.get("totals", {})}
