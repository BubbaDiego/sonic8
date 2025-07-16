import pytest
from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker
import backend.sonic_backend_app as app_module


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl


def test_update_snapshot_updates_session(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    resp = client.post(
        "/session/",
        json={"session_start_value": 100.0, "session_goal_value": 200.0},
    )
    assert resp.status_code == 201

    snapshot = {
        "total_size": 1.0,
        "total_value": 120.0,
        "total_collateral": 0.0,
        "avg_leverage": 1.0,
        "avg_travel_percent": 0.0,
        "avg_heat_index": 0.0,
        "total_heat_index": 0.0,
        "market_average_sp500": 0.0,
    }
    resp = client.post("/api/portfolio/update_snapshot", json=snapshot)
    assert resp.status_code == 200

    resp = client.get("/session/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_session_value"] == pytest.approx(20.0)
    assert data["session_performance_value"] == pytest.approx(20.0)

    latest = dl.portfolio.get_latest_snapshot()
    assert latest.session_start_value == pytest.approx(100.0)
    assert latest.session_goal_value == pytest.approx(200.0)
    assert latest.current_session_value == pytest.approx(20.0)
