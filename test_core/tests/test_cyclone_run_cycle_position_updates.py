import asyncio
import pytest
from cyclone import cyclone_engine
from cyclone.cyclone_engine import Cyclone
from positions.position_core import PositionCore
from data.data_locker import DataLocker


def _patch_seeding(monkeypatch):
    monkeypatch.setattr(DataLocker, "_seed_modifiers_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_wallets_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_thresholds_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alerts_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_ensure_travel_percent_threshold", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alert_config_if_empty", lambda self: None)


def dummy_update_positions(self, source="test"):
    self.dl.positions.insert_position({
        "id": "pos123",
        "asset_type": "BTC",
        "entry_price": 100.0,
        "liquidation_price": 50.0,
        "position_type": "LONG",
        "wallet_name": "w1",
        "current_heat_index": 0.0,
        "pnl_after_fees_usd": 0.0,
        "travel_percent": 0.0,
        "liquidation_distance": 0.1,
    })
    return {"success": True, "imported": 1}


@pytest.mark.asyncio
async def test_run_cycle_calls_position_updates(tmp_path, monkeypatch):
    _patch_seeding(monkeypatch)
    db_path = tmp_path / "cycle.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(cyclone_engine, "global_data_locker", dl)
    monkeypatch.setattr(PositionCore, "update_positions_from_jupiter", dummy_update_positions)

    called = {"run": False}
    original = Cyclone.run_position_updates

    async def wrapper(self):
        called["run"] = True
        await original(self)

    monkeypatch.setattr(Cyclone, "run_position_updates", wrapper)

    cyclone = Cyclone()
    await cyclone.run_cycle(steps=["position_updates"])

    rows = dl.positions.get_all_positions()
    assert called["run"]
    assert len(rows) == 1
    dl.db.close()

