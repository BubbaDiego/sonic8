import pytest
from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker
from backend.core.alert_core.threshold_service import ThresholdService
import backend.sonic_backend_app as app_module


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl


def test_liquidation_settings_persists(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    payload = {"threshold_percent": 2.5, "snooze_seconds": 123}
    resp = client.post("/api/monitor-settings/liquidation", json=payload)
    assert resp.status_code == 200

    cfg = dl.system.get_var("liquid_monitor")
    assert cfg["threshold_percent"] == pytest.approx(2.5)
    assert cfg["snooze_seconds"] == 123

    resp = client.get("/api/monitor-settings/liquidation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["threshold_percent"] == pytest.approx(2.5)
    assert data["snooze_seconds"] == 123


def test_profit_settings_persists(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    payload = {
        "portfolio_low": 10,
        "portfolio_high": 20,
        "single_low": 5,
        "single_high": 15,
    }
    resp = client.post("/api/monitor-settings/profit", json=payload)
    assert resp.status_code == 200

    ts = ThresholdService(dl.db)
    portfolio_th = ts.get_thresholds("TotalProfit", "Portfolio", "ABOVE")
    single_th = ts.get_thresholds("Profit", "Position", "ABOVE")
    assert portfolio_th.low == 10
    assert portfolio_th.high == 20
    assert single_th.low == 5
    assert single_th.high == 15

    resp = client.get("/api/monitor-settings/profit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["portfolio_low"] == 10
    assert data["portfolio_high"] == 20
    assert data["single_low"] == 5
    assert data["single_high"] == 15

