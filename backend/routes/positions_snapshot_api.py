from __future__ import annotations

from fastapi import APIRouter
from backend.core.reporting_core.sonic_reporting.positions_snapshot_v1 import (
    build_positions_snapshot,
)

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("/snapshot")
def get_positions_snapshot() -> dict:
    """Return unified rows + totals for dashboard & tools."""
    return build_positions_snapshot()
