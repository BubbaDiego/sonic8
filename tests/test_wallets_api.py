import types
from pathlib import Path
from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker
import backend.sonic_backend_app as app_module


def _setup_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl


def test_wallet_crud_flow(tmp_path, monkeypatch):
    client, dl = _setup_client(tmp_path, monkeypatch)

    # fresh DB should return empty list
    resp = client.get("/wallets/")
    assert resp.status_code == 200
    assert resp.json() == []

    # insert wallet
    wallet = {"name": "Test", "public_address": "abc"}
    resp = client.post("/wallets/", json=wallet)
    assert resp.status_code == 201

    # list now contains wallet
    resp = client.get("/wallets/")
    assert any(w["name"] == "Test" for w in resp.json())

    # update wallet
    updated = {"name": "Test", "public_address": "xyz", "chrome_profile": "Alt"}
    resp = client.put("/wallets/Test", json=updated)
    assert resp.status_code == 200

    resp = client.get("/wallets/")
    data = next(w for w in resp.json() if w["name"] == "Test")
    assert data["public_address"] == "xyz"

    # delete wallet
    resp = client.delete("/wallets/Test")
    assert resp.status_code == 200

    resp = client.get("/wallets/")
    assert resp.json() == []


def test_insert_star_wars_wallets(tmp_path, monkeypatch):
    client, dl = _setup_client(tmp_path, monkeypatch)

    resp = client.post("/wallets/star_wars")
    assert resp.status_code == 201
    data = resp.json()
    assert data.get("count", 0) > 0

    resp = client.get("/wallets/")
    assert resp.status_code == 200
    assert len(resp.json()) == data["count"]
