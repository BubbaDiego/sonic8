import pytest
from backend.core.positions_core.position_core import PositionCore
from data.data_locker import DataLocker
from backend.core.calc_core.calc_services import CalcServices
from backend.models.portfolio import PortfolioSnapshot
from backend.models.position import PositionDB


def test_totals_exclude_inactive(tmp_path):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    core = PositionCore(dl)

    active_pos = {
        "id": "pos1",
        "asset_type": "BTC",
        "position_type": "LONG",
        "size": 1.0,
        "value": 100.0,
        "collateral": 50.0,
        "leverage": 2.0,
        "travel_percent": 5.0,
        "status": "ACTIVE",
    }
    inactive_pos = {
        "id": "pos2",
        "asset_type": "ETH",
        "position_type": "SHORT",
        "size": 2.0,
        "value": 200.0,
        "collateral": 100.0,
        "leverage": 3.0,
        "travel_percent": 10.0,
        "status": "CLOSED",
    }

    core.create_position(active_pos)
    core.create_position(inactive_pos)

    core.record_snapshot()
    snap = dl.portfolio.get_latest_snapshot()

    assert isinstance(snap, PortfolioSnapshot)
    assert snap.total_value == active_pos["value"]
    assert snap.total_size == active_pos["size"]
    assert snap.total_collateral == active_pos["collateral"]


def test_calc_services_totals_with_objects():
    calc = CalcServices()
    positions = [
        PositionDB(
            id="p1",
            size=1.0,
            value=100.0,
            collateral=50.0,
            leverage=2.0,
            travel_percent=5.0,
        ),
        PositionDB(
            id="p2",
            size=2.0,
            value=200.0,
            collateral=100.0,
            leverage=3.0,
            travel_percent=10.0,
        ),
    ]

    totals = calc.calculate_totals(positions)

    assert totals["total_value"] == 300.0
    assert totals["total_size"] == 3.0
    assert totals["total_collateral"] == 150.0
    assert totals["avg_leverage"] == pytest.approx((2.0 * 1.0 + 3.0 * 2.0) / 3.0)
    assert totals["avg_travel_percent"] == pytest.approx((5.0 * 1.0 + 10.0 * 2.0) / 3.0)

