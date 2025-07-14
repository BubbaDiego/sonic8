from fastapi.testclient import TestClient
import backend.sonic_backend_app as app_module
from backend.data.data_locker import DataLocker


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl


def test_start_and_get_session(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)

    payload = {"session_start_value": 100.0, "session_goal_value": 200.0, "notes": "test"}
    resp = client.post("/session/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["session_start_value"] == 100.0

    resp = client.get("/session/")
    assert resp.status_code == 200
    active = resp.json()
    assert active["id"] == data["id"]


def test_update_and_close_session(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)
    resp = client.post("/session/", json={"session_start_value": 1, "session_goal_value": 2})
    sid = resp.json()["id"]

    resp = client.put(f"/session/{sid}", json={"notes": "hello"})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "hello"

    resp = client.post("/session/close")
    assert resp.status_code == 200
    assert resp.json()["status"] == "CLOSED"
