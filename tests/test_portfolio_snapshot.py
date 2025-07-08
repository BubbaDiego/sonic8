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
        total_heat_index=0.2,
        market_average_sp500=100.0,
    )
    mgr.record_snapshot(snap)
    latest = mgr.get_latest_snapshot()
    assert isinstance(latest, PortfolioSnapshot)
    assert latest.total_value == snap.total_value
    assert latest.total_heat_index == snap.total_heat_index
    assert latest.market_average_sp500 == 100.0
    assert latest.session_start_value == 0.0
    assert latest.current_session_value == 0.0
    assert latest.session_goal_value == 0.0
    assert latest.session_performance_value == 0.0
    all_snaps = mgr.get_snapshots()
    assert len(all_snaps) == 1
    assert isinstance(all_snaps[0], PortfolioSnapshot)
    assert all_snaps[0].total_size == snap.total_size
    assert all_snaps[0].total_heat_index == snap.total_heat_index
    assert all_snaps[0].market_average_sp500 == 100.0


def test_session_value_computed(dl_tmp):
    mgr = dl_tmp.portfolio
    snap = PortfolioSnapshot(
        total_size=1.0,
        total_value=20.0,
        total_collateral=1.0,
        avg_leverage=1.0,
        avg_travel_percent=0.0,
        avg_heat_index=0.0,
        total_heat_index=0.0,
        market_average_sp500=0.0,
        session_start_value=15.0,
        current_session_value=999.0,
    )
    mgr.record_snapshot(snap)
    latest = mgr.get_latest_snapshot()
    assert latest.current_session_value == 5.0

