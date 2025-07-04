import pytest
from data.data_locker import DataLocker
from cyclone.cyclone_maintenance_service import CycloneMaintenanceService
from backend.models.portfolio import PortfolioSnapshot


def test_clear_positions_resets_portfolio(dl_tmp):
    # record a snapshot so the table is not empty
    snap = PortfolioSnapshot(
        total_size=1.0,
        total_value=1.0,
        total_collateral=1.0,
        avg_leverage=1.0,
        avg_travel_percent=0.0,
        avg_heat_index=0.0,
    )
    dl_tmp.portfolio.record_snapshot(snap)
    assert dl_tmp.portfolio.get_snapshots()  # sanity check

    maint = CycloneMaintenanceService(dl_tmp)
    maint.clear_positions()

    assert dl_tmp.portfolio.get_snapshots() == []
