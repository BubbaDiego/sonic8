import json
from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker
from backend.core import constants
from backend.data import dl_thresholds
import backend.sonic_backend_app as app_module


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    json_path = tmp_path / "alert_thresholds.json"
    monkeypatch.setattr(constants, "ALERT_THRESHOLDS_PATH", json_path)
    monkeypatch.setattr(dl_thresholds, "ALERT_THRESHOLDS_JSON_PATH", str(json_path))
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl, json_path


def test_get_bulk(tmp_path, monkeypatch):
    client, dl, path = _setup(tmp_path, monkeypatch)
    resp = client.get("/alert_thresholds/bulk")
    assert resp.status_code == 200
    data = resp.json()
    assert "thresholds" in data
    assert "cooldowns" in data
    with open(path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert data["cooldowns"] == saved.get("cooldowns")


def test_put_bulk_replaces(tmp_path, monkeypatch):
    client, dl, path = _setup(tmp_path, monkeypatch)
    new_cfg = {
        "thresholds": [
            {
                "id": "t1",
                "alert_type": "X",
                "alert_class": "Y",
                "metric_key": "m",
                "condition": "ABOVE",
                "low": 1,
                "medium": 2,
                "high": 3,
                "enabled": True,
                "last_modified": "2020-01-01T00:00:00+00:00",
                "low_notify": "",
                "medium_notify": "",
                "high_notify": "",
            }
        ],
        "cooldowns": {
            "alert_cooldown_seconds": 1,
            "call_refractory_period": 2,
            "snooze_countdown": 3,
        },
    }
    resp = client.put("/alert_thresholds/bulk", json=new_cfg)
    assert resp.status_code == 200
    resp = client.get("/alert_thresholds/bulk")
    data = resp.json()
    assert data["cooldowns"]["alert_cooldown_seconds"] == 1
    assert len(data["thresholds"]) == 1
    assert data["thresholds"][0]["id"] == "t1"
    mgr = dl_thresholds.DLThresholdManager(dl.db)
    all_thr = mgr.get_all()
    assert len(all_thr) == 1
    assert all_thr[0].id == "t1"


def test_post_threshold_creates_row(tmp_path, monkeypatch):
    client, dl, _ = _setup(tmp_path, monkeypatch)
    mgr = dl_thresholds.DLThresholdManager(dl.db)

    payload = {
        "id": "ld1",
        "alert_type": "LiquidationDistance",
        "alert_class": "Position",
        "metric_key": "liquidation_distance",
        "condition": "BELOW",
        "low": 1.0,
        "medium": 2.0,
        "high": 3.0,
        "enabled": True,
        "last_modified": "2020-01-01T00:00:00+00:00",
        "low_notify": "",
        "medium_notify": "",
        "high_notify": "",
    }

    resp = client.post("/alert_thresholds/", json=payload)
    assert resp.status_code == 201
    assert resp.json() == payload

    row = mgr.get_by_id("ld1")
    assert row is not None
    assert row.to_dict() == payload
