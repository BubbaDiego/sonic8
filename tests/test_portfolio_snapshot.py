import pytest
from backend.models.portfolio import PortfolioSnapshot
from data.data_locker import DataLocker

def test_record_and_fetch_snapshot(dl_tmp):
    mgr = dl_tmp.portfolio
    snap = PortfolioSnapshot(
        total_size=1.0,
        total_value=2.0,
        total_collateral=1.0,
        avg_leverage=1.5,
        avg_travel_percent=0.1,
        avg_heat_index=0.2,
    )
    mgr.record_snapshot(snap)
    latest = mgr.get_latest_snapshot()
    assert isinstance(latest, PortfolioSnapshot)
    assert latest.total_value == snap.total_value
    all_snaps = mgr.get_snapshots()
    assert len(all_snaps) == 1
    assert isinstance(all_snaps[0], PortfolioSnapshot)
    assert all_snaps[0].total_size == snap.total_size

