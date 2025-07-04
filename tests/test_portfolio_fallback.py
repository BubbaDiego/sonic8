import backend.sonic_backend_app as app_module
from backend.data.data_locker import DataLocker
import pytest
from fastapi.testclient import TestClient


def test_portfolio_latest_null_fallback(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    # insert sample positions
    dl.positions.create_position({"value": 10, "size": 2, "leverage": 3})
    dl.positions.create_position({"value": 15, "size": 3, "leverage": 5})

    client = TestClient(app_module.app)
    resp = client.get("/portfolio/latest")
    assert resp.status_code == 200
    assert resp.json() is None

    resp = client.get("/positions/")
    assert resp.status_code == 200
    positions = resp.json()

    total = sum(float(p.get("value") or 0) for p in positions)
    assert total == 25

    size_total = sum(float(p.get("size") or 0) for p in positions)
    assert size_total == 5

    leverage = (
        sum(float(p.get("leverage") or 0) * float(p.get("size") or 1) for p in positions) / size_total
    )
    assert leverage == pytest.approx(4.2)
