import pytest
from data.data_locker import DataLocker
from cyclone.cyclone_maintenance_service import CycloneMaintenanceService
from backend.models.portfolio import PortfolioSnapshot


def test_clear_positions_keeps_portfolio_history(dl_tmp):
    """Positions are removed but portfolio snapshots remain."""
    # record a snapshot so the table is not empty
    snap = PortfolioSnapshot(
        total_size=1.0,
        total_value=1.0,
        total_collateral=1.0,
        avg_leverage=1.0,
        avg_travel_percent=0.0,
        avg_heat_index=0.0,
        market_average_sp500=120.0,
    )
    dl_tmp.portfolio.record_snapshot(snap)
    assert dl_tmp.portfolio.get_snapshots()  # sanity check

    before = dl_tmp.portfolio.get_snapshots()

    maint = CycloneMaintenanceService(dl_tmp)
    maint.clear_positions()

    after = dl_tmp.portfolio.get_snapshots()
    assert len(after) == len(before) == 1
    assert after[0].id == before[0].id
    assert after[0].market_average_sp500 == 120.0
