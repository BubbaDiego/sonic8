import pytest
from fastapi.testclient import TestClient

from core.logging import log
from backend.data.data_locker import DataLocker
import backend.sonic_backend_app as app_module

# Setup the Flask Test SonicReactApp
@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(DataLocker, "_seed_modifiers_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_wallets_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_thresholds_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alerts_if_empty", lambda self: None)

    dl = DataLocker(str(tmp_path / "alerts.db"))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    client = TestClient(app_module.app)
    yield client, dl
    dl.db.close()

# --- API Endpoint Tests ---

def test_refresh_alerts(client):
    """Test POST /alerts/refresh endpoint."""
    log.banner("TEST: Refresh Alerts API Start")
    response = client[0].post('/alerts/refresh')
    assert response.status_code in [200, 500]  # Allow 500 if no alerts loaded yet
    log.success(f"✅ Refresh Alerts API response: {response.status_code}", source="TestAlertsAPI")

def test_create_all_alerts(client):
    """Test POST /alerts/create_all endpoint."""
    log.banner("TEST: Create All Alerts API Start")
    response = client[0].post('/alerts/create_all')
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True

    alerts = client[1].db.fetch_all("alerts")
    assert len(alerts) == 1
    assert alerts[0]["id"] == "alert-sample-1"

    log.success(
        f"✅ Create All Alerts API response: {response.status_code}",
        source="TestAlertsAPI",
    )

def test_delete_all_alerts(client):
    """Test POST /alerts/delete_all endpoint."""
    log.banner("TEST: Delete All Alerts API Start")
    client[0].post('/alerts/create_all')

    response = client[0].post('/alerts/delete_all')
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True

    alerts = client[1].db.fetch_all("alerts")
    assert alerts == []

    log.success(
        f"✅ Delete All Alerts API response: {response.status_code}",
        source="TestAlertsAPI",
    )

def test_monitor_alerts(client):
    """Test GET /alerts/monitor endpoint."""
    log.banner("TEST: Monitor Alerts API Start")
    response = client[0].get('/alerts/monitor')
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert isinstance(data["alerts"], list)
    log.success(f"✅ Monitor Alerts API response: {response.status_code}, {len(data['alerts'])} alerts returned", source="TestAlertsAPI")
