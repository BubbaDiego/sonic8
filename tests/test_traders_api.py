from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker
import backend.sonic_backend_app as app_module


def _setup_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl


def test_get_traders_returns_data(tmp_path, monkeypatch):
    client, dl = _setup_client(tmp_path, monkeypatch)
    dl.traders.create_trader({"name": "Alice"})
    resp = client.get("/traders/")
    assert resp.status_code == 200
    assert any(t["name"] == "Alice" for t in resp.json())

