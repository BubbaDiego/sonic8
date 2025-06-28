import importlib
import pytest

from data.data_locker import DataLocker
from calc_core.calc_services import CalcServices


@pytest.mark.asyncio
async def test_run_aggregate_positions_updates_fields(tmp_path, monkeypatch):
    for name in [
        "_seed_modifiers_if_empty",
        "_seed_wallets_if_empty",
        "_seed_thresholds_if_empty",
        "_seed_alerts_if_empty",
    ]:
        monkeypatch.setattr(DataLocker, name, lambda self: None)

    import cyclone.cyclone_engine as ce
    dl = DataLocker(str(tmp_path / "agg.db"))
    monkeypatch.setattr(ce, "global_data_locker", dl)
    engine = ce.Cyclone()

    dl.positions.create_position({
        "id": "p1",
        "asset_type": "BTC",
        "position_type": "LONG",
        "entry_price": 100.0,
        "current_price": 90.0,
        "liquidation_price": 80.0,
        "size": 1.0,
        "wallet_name": "test",
        "last_updated": "now",
        "pnl_after_fees_usd": 0.0,
        "travel_percent": 0.0,
        "liquidation_distance": 0.0,
        "current_heat_index": 0.0,
    })

    await engine.run_aggregate_positions()

    stored = dl.positions.get_position_by_id("p1")
    expected = CalcServices().calculate_travel_percent("LONG", 100.0, 90.0, 80.0)
    assert stored["travel_percent"] == expected
    dl.db.close()
