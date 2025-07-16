import pytest

from backend.models.portfolio import PortfolioSnapshot


def _create_snapshot(mgr, **kwargs):
    snap = PortfolioSnapshot(
        total_size=1.0,
        total_value=kwargs.get("total_value", 0.0),
        total_collateral=1.0,
        avg_leverage=1.0,
        avg_travel_percent=0.0,
        avg_heat_index=0.0,
        total_heat_index=0.0,
        market_average_sp500=0.0,
        session_start_value=kwargs.get("session_start_value", 0.0),
    )
    mgr.record_snapshot(snap)
    return mgr.get_latest_snapshot()


def test_update_entry_recomputes_with_total_only(dl_tmp):
    mgr = dl_tmp.portfolio
    latest = _create_snapshot(mgr, total_value=100.0)

    mgr.update_entry(latest.id, {"total_value": 150.0})
    updated = mgr.get_entry_by_id(latest.id)

    assert updated["total_value"] == 150.0
    assert updated["current_session_value"] == pytest.approx(150.0)
    assert updated["session_performance_value"] == pytest.approx(150.0)


def test_update_entry_recomputes_with_start_only(dl_tmp):
    mgr = dl_tmp.portfolio
    latest = _create_snapshot(mgr, total_value=200.0, session_start_value=50.0)

    mgr.update_entry(latest.id, {"session_start_value": 40.0})
    updated = mgr.get_entry_by_id(latest.id)

    expected_delta = 200.0 - 40.0
    assert updated["session_start_value"] == 40.0
    assert updated["current_session_value"] == pytest.approx(expected_delta)
    assert updated["session_performance_value"] == pytest.approx(expected_delta)

