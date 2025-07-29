import types
from fastapi.testclient import TestClient
from backend.data.data_locker import DataLocker
import backend.sonic_backend_app as app_module
import backend.routes.monitor_api_adapter as adapter


def test_sonic_cycle_route(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    # Patch Cyclone and sonic_cycle to avoid heavy operations
    monkeypatch.setattr(adapter, "Cyclone", lambda: object())

    async def fake_cycle(loop_counter, cyclone):
        return None
    monkeypatch.setattr(adapter, "sonic_cycle", fake_cycle)

    client = TestClient(app_module.app)
    resp = client.post("/monitors/sonic_cycle")
    assert resp.status_code == 202
    assert resp.json()["status"] == "sonic cycle started"
