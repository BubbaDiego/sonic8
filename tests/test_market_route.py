from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker
from backend.routes.market_api import router as market_router


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    app = FastAPI()
    app.include_router(market_router)
    client = TestClient(app)
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


def test_latest_skips_entries_missing_windows(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)
    meta = {
        "details": [
            {"asset": "BTC", "windows": {"24h": {"pct_move": 42}}},
            {"asset": "ETH"},
        ]
    }
    dl.ledger.insert_ledger_entry("market_monitor", status="Success", metadata=meta)

    resp = client.get("/api/market/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert "BTC" in data
    assert "ETH" not in data


def test_latest_normalizes_market_movement_details(tmp_path, monkeypatch):
    client, dl = _setup(tmp_path, monkeypatch)
    meta = {
        "details": [
            {
                "asset": "SOL",
                "anchor": {"value": "98.5", "time": "2024-02-28T00:00:00Z"},
                "current": "100.5",
                "threshold": "1.5",
                "direction": "UP",
                "dir_ok": 1,
                "triggered": 0,
            },
            {
                "asset": "BTC",
                "anchor": "10",
                "price": "12",
                "delta": "0.5",
                "trigger": "True",
                "dir_ok": "false",
            },
        ]
    }
    dl.ledger.insert_ledger_entry("market_monitor", status="Success", metadata=meta)

    resp = client.get("/api/market/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "SOL": {
            "anchor": 98.5,
            "current": 100.5,
            "move": 2.0,
            "threshold": 1.5,
            "direction": "up",
            "dir_ok": True,
            "triggered": False,
        },
        "BTC": {
            "anchor": 10.0,
            "current": 12.0,
            "move": 2.0,
            "threshold": 0.5,
            "direction": "both",
            "dir_ok": False,
            "triggered": True,
        },
    }
