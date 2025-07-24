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

    payload = {
        "threshold_percent": 2.5,
        "snooze_seconds": 123,
        "thresholds": {"BTC": 1.2, "ETH": 3.4},
    }
    resp = client.post("/api/monitor-settings/liquidation", json=payload)
    assert resp.status_code == 200

    cfg = dl.system.get_var("liquid_monitor")
    assert cfg["threshold_percent"] == pytest.approx(2.5)
    assert cfg["snooze_seconds"] == 123
    assert cfg["thresholds"] == {"BTC": 1.2, "ETH": 3.4}

    resp = client.get("/api/monitor-settings/liquidation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["threshold_percent"] == pytest.approx(2.5)
    assert data["snooze_seconds"] == 123
    assert data["thresholds"] == {"BTC": 1.2, "ETH": 3.4}


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


@pytest.mark.parametrize("value", ["false", "0"])
def test_liquidation_settings_bool_parsing_legacy(tmp_path, monkeypatch, value):
    client, dl = _setup(tmp_path, monkeypatch)

    payload = {
        "windows_alert": value,
        "voice_alert": value,
        "sms_alert": value,
    }
    resp = client.post("/api/monitor-settings/liquidation", json=payload)
    assert resp.status_code == 200

    cfg = dl.system.get_var("liquid_monitor")
    assert cfg["windows_alert"] is False
    assert cfg["voice_alert"] is False
    assert cfg["sms_alert"] is False
    assert cfg["notifications"] == {"system": False, "voice": False, "sms": False}


@pytest.mark.parametrize("value", ["false", "0"])
def test_liquidation_settings_bool_parsing_new(tmp_path, monkeypatch, value):
    client, dl = _setup(tmp_path, monkeypatch)

    payload = {"notifications": {"system": value, "voice": value, "sms": value}}
    resp = client.post("/api/monitor-settings/liquidation", json=payload)
    assert resp.status_code == 200

    cfg = dl.system.get_var("liquid_monitor")
    assert cfg["windows_alert"] is False
    assert cfg["voice_alert"] is False
    assert cfg["sms_alert"] is False
    assert cfg["notifications"] == {"system": False, "voice": False, "sms": False}

