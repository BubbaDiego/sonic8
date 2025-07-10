from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker
import backend.sonic_backend_app as app_module


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl


def test_list_and_read_table(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)
    dl.create_wallet({"name": "Test", "public_address": "abc"})

    resp = client.get("/db_admin/tables")
    assert resp.status_code == 200
    assert "wallets" in resp.json()

    resp = client.get("/db_admin/tables/wallets?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert any(row["name"] == "Test" for row in data)
