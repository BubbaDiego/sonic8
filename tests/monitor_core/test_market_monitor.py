from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import backend.sonic_backend_app as app_module
from backend.data.data_locker import DataLocker


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl


def test_settings_roundtrip(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    payload = {
        "thresholds": {"BTC": {"delta": 15.0, "direction": "up"}},
        "rearm_mode": "reset",
        "notifications": {"system": False, "voice": False, "sms": False, "tts": True},
    }

    resp = client.post("/api/monitor-settings/market", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["thresholds"]["BTC"]["delta"] == pytest.approx(15.0)
    assert data["thresholds"]["BTC"]["direction"] == "up"
    assert data["rearm_mode"] == "reset"
    assert data["notifications"]["system"] is False

    resp = client.get("/api/monitor-settings/market")
    assert resp.status_code == 200
    fetched = resp.json()
    assert fetched["thresholds"]["BTC"]["delta"] == pytest.approx(15.0)
    assert fetched["rearm_mode"] == "reset"


def test_reset_anchors(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    now = datetime.now(timezone.utc).isoformat()
    dl.prices.insert_price(
        {
            "asset_type": "BTC",
            "current_price": 100.0,
            "previous_price": 0.0,
            "previous_update_time": None,
            "last_update_time": now,
            "source": "test",
        }
    )

    resp = client.post("/api/monitor-settings/market/reset-anchors")
    assert resp.status_code == 200
    cfg = resp.json()
    assert cfg["anchors"]["BTC"]["value"] == pytest.approx(100.0)
    assert cfg["armed"]["BTC"] is True
