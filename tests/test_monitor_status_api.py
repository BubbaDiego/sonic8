from fastapi.testclient import TestClient
import backend.sonic_backend_app as app_module


def test_monitor_status_update():
    client = TestClient(app_module.app)

    resp = client.get("/monitor_status/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["monitors"]["Sonic Monitoring"]["status"] == "Offline"

    resp = client.post("/monitor_status/SONIC", json={"status": "Healthy"})
    assert resp.status_code == 200

    resp = client.get("/monitor_status/SONIC")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["status"] == "Healthy"

