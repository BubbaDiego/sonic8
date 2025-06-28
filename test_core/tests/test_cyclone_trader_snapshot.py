import types
import importlib
import pytest
from data.data_locker import DataLocker


def _patch_seeding(monkeypatch):
    monkeypatch.setattr(DataLocker, "_seed_modifiers_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_wallets_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_thresholds_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alerts_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_ensure_travel_percent_threshold", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alert_config_if_empty", lambda self: None)

class DummyLoader:
    def __init__(self, data_locker):
        self.persona_manager = types.SimpleNamespace(list_personas=lambda: ["TestBot"])
    def load_trader(self, name):
        return types.SimpleNamespace(
            name=name,
            wallet_balance=100.0,
            portfolio={"total_value": 150.0},
            heat_index=10.0,
            mood="happy",
            strategies={"s": 1},
        )

@pytest.mark.asyncio
async def test_run_cycle_logs_trader_snapshot(tmp_path, monkeypatch):
    _patch_seeding(monkeypatch)
    db_path = tmp_path / "cycle.db"
    learn_path = tmp_path / "learn.db"
    monkeypatch.setenv("LEARNING_DB_PATH", str(learn_path))
    monkeypatch.setenv("LEARNING_SAMPLING_SEC", "0")
    import learning_database.learning_event_logger as logger
    importlib.reload(logger)

    import cyclone.cyclone_engine as engine
    importlib.reload(engine)

    dl = DataLocker(str(db_path))
    monkeypatch.setattr(engine, "global_data_locker", dl)
    monkeypatch.setattr(engine, "TraderLoader", DummyLoader)

    cyclone = engine.Cyclone()
    await cyclone.run_cycle(steps=[])

    rows = logger.LearningDataLocker.get_instance().db.fetch_all("trader_snapshots")
    assert len(rows) == 1
    assert rows[0]["trader_name"] == "TestBot"
    dl.db.close()
    logger.LearningDataLocker.get_instance().db.close()

