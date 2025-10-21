import pytest
from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker
from backend.core.alert_core.threshold_service import ThresholdService
import backend.sonic_backend_app as app_module
from backend.core.monitor_core.sonic_monitor import MONITOR_NAME


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl


def test_liquidation_settings_persists(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    payload = {
        "thresholds": {"BTC": "1.2", "ETH": "3.4"},
        "blast_radius": {"BTC": "4", "ETH": "6"},
        "notifications": {"system": True, "voice": False, "sms": True, "tts": False},
        "enabled_liquid": False,
    }
    resp = client.post("/api/monitor-settings/liquidation", json=payload)
    assert resp.status_code == 204

    cfg = dl.system.get_var("liquid_monitor")
    assert cfg["thresholds"] == {"BTC": 1.2, "ETH": 3.4}
    assert cfg["blast_radius"] == {"BTC": 4.0, "ETH": 6.0}
    assert cfg["notifications"] == {"system": True, "voice": False, "sms": True, "tts": False}
    assert cfg["enabled_liquid"] is False
    assert cfg["enabled"] is False
    assert "threshold_percent" not in cfg

    resp = client.get("/api/monitor-settings/liquidation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["thresholds"] == {"BTC": 1.2, "ETH": 3.4}
    assert data["blast_radius"] == {"BTC": 4.0, "ETH": 6.0}
    assert data["notifications"] == {"system": True, "voice": False, "sms": True, "tts": False}
    assert data["enabled_liquid"] is False


def test_liquidation_rejects_threshold_percent(tmp_path, monkeypatch):
    client, _ = _setup(tmp_path, monkeypatch)

    resp = client.post(
        "/api/monitor-settings/liquidation",
        json={"threshold_percent": 5.0},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "threshold_percent removed; set per-asset thresholds instead."


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


def test_profit_notifications_roundtrip(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    payload = {
        "notifications": {
            "system": False,
            "voice": False,
            "sms": True,
            "tts": False,
        }
    }
    resp = client.post("/api/monitor-settings/profit", json=payload)
    assert resp.status_code == 200

    cfg = dl.system.get_var("profit_monitor")
    assert cfg["notifications"] == {
        "system": False,
        "voice": False,
        "sms": True,
        "tts": False,
    }

    resp = client.get("/api/monitor-settings/profit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["notifications"] == {
        "system": False,
        "voice": False,
        "sms": True,
        "tts": False,
    }


def test_liq_notifications_merge(tmp_path, monkeypatch):
    """Legacy payload keys should merge into nested notifications."""
    client, dl = _setup(tmp_path, monkeypatch)

    payload = {
        "threshold_btc": 0.9,
        "threshold_eth": 0.7,
        "windows_alert": False,
        "voice_alert": False,
        "sms_alert": True,
        "tts_alert": False,
    }

    resp = client.post("/api/monitor-settings/liquidation", json=payload)
    assert resp.status_code == 204

    cfg = dl.system.get_var("liquid_monitor")
    assert cfg["thresholds"] == {"BTC": 0.9, "ETH": 0.7}
    assert cfg["notifications"] == {
        "system": False,
        "voice": False,
        "sms": True,
        "tts": False,
    }
    assert cfg["windows_alert"] is False
    assert cfg["voice_alert"] is False
    assert cfg["sms_alert"] is True
    assert cfg["tts_alert"] is False
    assert "threshold_percent" not in cfg

    resp = client.get("/api/monitor-settings/liquidation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["notifications"] == {
        "system": False,
        "voice": False,
        "sms": True,
        "tts": False,
    }
    assert data["windows_alert"] is False
    assert data["voice_alert"] is False
    assert data["sms_alert"] is True
    assert data["tts_alert"] is False
    assert data["thresholds"] == {"BTC": 0.9, "ETH": 0.7}


def test_sonic_settings_roundtrip(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    resp = client.get("/api/monitor-settings/sonic")
    assert resp.status_code == 200
    data = resp.json()
    assert data["interval_seconds"] == 60
    assert data["enabled_sonic"] is True
    assert data["enabled_liquid"] is True
    assert data["enabled_profit"] is True
    assert data["enabled_market"] is True

    payload = {
        "interval_seconds": 42,
        "enabled_sonic": False,
        "enabled_liquid": False,
        "enabled_profit": True,
        "enabled_market": False,
    }
    resp = client.post("/api/monitor-settings/sonic", json=payload)
    assert resp.status_code == 200

    cursor = dl.db.get_cursor()
    cursor.execute(
        "SELECT interval_seconds FROM monitor_heartbeat WHERE monitor_name = ?",
        (MONITOR_NAME,),
    )
    row = cursor.fetchone()
    assert row[0] == 42

    cfg = dl.system.get_var("sonic_monitor")
    assert cfg == {
        "enabled_sonic": False,
        "enabled_liquid": False,
        "enabled_profit": True,
        "enabled_market": False,
    }

    resp = client.get("/api/monitor-settings/sonic")
    assert resp.status_code == 200
    data = resp.json()
    assert data["interval_seconds"] == 42
    assert data["enabled_sonic"] is False
    assert data["enabled_liquid"] is False
    assert data["enabled_profit"] is True
    assert data["enabled_market"] is False


def test_profit_enabled_roundtrip(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    resp = client.post("/api/monitor-settings/profit", json={"enabled": False})
    assert resp.status_code == 200

    cfg = dl.system.get_var("profit_monitor")
    assert cfg["enabled"] is False

    resp = client.get("/api/monitor-settings/profit")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


def test_liquidation_enabled_roundtrip(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    resp = client.post(
        "/api/monitor-settings/liquidation",
        json={"enabled": False},
    )
    assert resp.status_code == 204

    cfg = dl.system.get_var("liquid_monitor")
    assert cfg["enabled"] is False
    assert cfg["enabled_liquid"] is False

    resp = client.get("/api/monitor-settings/liquidation")
    assert resp.status_code == 200
    assert resp.json()["enabled_liquid"] is False
    assert resp.json()["enabled"] is False
