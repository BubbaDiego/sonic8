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
    resp = client.get("/api/traders/")
    assert resp.status_code == 200
    assert any(t["name"] == "Alice" for t in resp.json())


def test_export_traders(tmp_path, monkeypatch):
    import json
    from data import dl_traders as dl_t

    client, dl = _setup_client(tmp_path, monkeypatch)
    json_path = tmp_path / "active_traders.json"
    monkeypatch.setattr(dl_t, "ACTIVE_TRADERS_JSON_PATH", json_path)

    dl.traders.create_trader({"name": "Alice"})
    resp = client.get("/traders/export")
    assert resp.status_code == 200
    assert json_path.exists()
    data = json.loads(json_path.read_text())
    assert any(t["name"] == "Alice" for t in data)


def test_seed_traders_on_init(tmp_path, monkeypatch):
    import json
    from data import dl_traders as dl_t

    json_path = tmp_path / "active_traders.json"
    json_path.write_text(json.dumps([{"name": "Seeded"}]))
    monkeypatch.setattr(dl_t, "ACTIVE_TRADERS_JSON_PATH", json_path)

    client, dl = _setup_client(tmp_path, monkeypatch)
    resp = client.get("/api/traders/")
    assert resp.status_code == 200
    assert any(t["name"] == "Seeded" for t in resp.json())

