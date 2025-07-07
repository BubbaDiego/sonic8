from fastapi.testclient import TestClient
import backend.sonic_backend_app as app_module
from backend.data.data_locker import DataLocker


def test_monitor_status_update(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    client = TestClient(app_module.app)

    resp = client.get("/monitor_status/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["monitors"]["Sonic Monitoring"]["status"] == "Offline"

    dl.ledger.insert_ledger_entry("sonic_monitor", status="Success", metadata={})

    resp = client.get("/monitor_status/SONIC")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["status"] == "Healthy"

