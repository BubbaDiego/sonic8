import backend.sonic_backend_app as app_module
from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    return client, dl


def test_latest_ignores_error_entries(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)
    success_meta = {
        "details": [
            {"asset": "BTC", "windows": {"24h": {"pct_move": 42, "threshold": 5, "trigger": True}}}
        ]
    }
    dl.ledger.insert_ledger_entry("market_monitor", status="Success", metadata=success_meta)
    dl.ledger.insert_ledger_entry("market_monitor", status="Error", metadata={"details": []})

    resp = client.get("/api/market/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("BTC") is not None
    assert data["BTC"]["24h"]["pct_move"] == 42
