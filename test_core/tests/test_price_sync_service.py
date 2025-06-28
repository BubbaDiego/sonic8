import importlib

from data.data_locker import DataLocker
from prices.price_sync_service import PriceSyncService


def _setup_datalocker(tmp_path, monkeypatch):
    monkeypatch.setattr(DataLocker, "_seed_modifiers_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_wallets_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_thresholds_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alerts_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alert_config_if_empty", lambda self: None)
    return DataLocker(str(tmp_path / "main.db"))


def test_price_tick_logged(monkeypatch, tmp_path):
    learning_db = tmp_path / "learning.db"
    monkeypatch.setenv("LEARNING_DB_PATH", str(learning_db))
    import learning_database.learning_event_logger as logger
    logger = importlib.reload(logger)

    dl = _setup_datalocker(tmp_path, monkeypatch)
    svc = PriceSyncService(dl)
    monkeypatch.setattr(svc.service, "fetch_prices", lambda: {"BTC": 1.0, "ETH": 2.0})

    svc.run_full_price_sync(source="test")

    ldl = logger.LearningDataLocker.get_instance()
    rows = ldl.db.fetch_all("price_ticks")
    assert len(rows) == 1
    assert rows[0]["asset_type"] == "BTC"
    assert rows[0]["price"] == 1.0
    dl.db.close()
    ldl.db.close()
