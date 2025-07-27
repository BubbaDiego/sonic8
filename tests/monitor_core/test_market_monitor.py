import types
import pytest
from fastapi.testclient import TestClient

from backend.data.data_locker import DataLocker
import backend.sonic_backend_app as app_module
from backend.core.monitor_core import market_monitor


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl


def test_market_settings_persists(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    payload = {
        "thresholds": {"BTC": 2.5},
        "baseline": {
            "BTC": {"price": 100.0, "timestamp": "2024-01-01T00:00:00+00:00", "mode": "EITHER"}
        },
        "blast_filters": {"window": "24h", "exchange": "binance"},
    }

    resp = client.post("/api/monitor-settings/market", json=payload)
    assert resp.status_code == 200

    cfg = dl.system.get_var("market_monitor")
    assert cfg["thresholds"]["BTC"] == pytest.approx(2.5)
    assert cfg["baseline"]["BTC"]["price"] == pytest.approx(100.0)

    resp = client.get("/api/monitor-settings/market")
    assert resp.status_code == 200
    data = resp.json()
    assert data["thresholds"]["BTC"] == pytest.approx(2.5)
    assert data["baseline"]["BTC"]["price"] == pytest.approx(100.0)


def test_market_settings_defaults(tmp_path, monkeypatch):
    client, _ = _setup(tmp_path, monkeypatch)

    resp = client.get("/api/monitor-settings/market")
    assert resp.status_code == 200
    data = resp.json()

    assert data["blast_radius"]["BTC"] == pytest.approx(8000.0)
    assert data["blast_radius"]["ETH"] == pytest.approx(300.0)
    assert data["blast_radius"]["SOL"] == pytest.approx(13.0)


def test_do_work_updates_blast_and_threshold(monkeypatch):
    price_map = {"BTC": 110.0, "ETH": 102.0, "SOL": 98.0}
    cfg = {
        "baseline": {
            "BTC": {"price": 100.0, "timestamp": "2024-01-01T00:00:00+00:00", "mode": "EITHER"},
            "ETH": {"price": 100.0, "timestamp": "2024-01-01T00:00:00+00:00", "mode": "EITHER"},
            "SOL": {"price": 100.0, "timestamp": "2024-01-01T00:00:00+00:00", "mode": "EITHER"},
        },
        "thresholds": {"BTC": 5.0, "ETH": 5.0, "SOL": 5.0},
        "blast_radius": {"BTC": 8000.0, "ETH": 300.0, "SOL": 13.0},
        "blast_filters": {"window": "24h", "exchange": "coingecko"},
    }

    class FakeDL:
        def __init__(self):
            self.config = {"market_monitor": cfg}
            self.system = types.SimpleNamespace(
                get_var=lambda key: self.config.get(key),
                set_var=lambda key, val: self.config.__setitem__(key, val),
            )

        def get_latest_price(self, asset):
            return {"current_price": price_map[asset]}

    dl = FakeDL()
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    swing_data = {
        "BTC": {"high": 120.0, "low": 100.0},
        "ETH": {"high": 110.0, "low": 100.0},
        "SOL": {"high": 105.0, "low": 95.0},
    }
    monkeypatch.setattr(
        market_monitor, "DailySwingService", lambda: types.SimpleNamespace(fetch=lambda assets: swing_data)
    )

    monitor = market_monitor.MarketMonitor()
    result = monitor._do_work()

    assert result["trigger_any"] is True
    updated = dl.system.get_var("market_monitor")
    assert updated["blast_radius"]["BTC"] == pytest.approx(20.0)
    assert result["details"][0]["trigger"] is True
    assert result["details"][1]["trigger"] is False
