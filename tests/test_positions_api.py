import types
from pathlib import Path
from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker
import backend.sonic_backend_app as app_module


def test_positions_list_empty(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    client = TestClient(app_module.app)
    resp = client.get("/positions/")
    assert resp.status_code == 200
    assert resp.json() == []

