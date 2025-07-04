import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from backend.data.data_locker import DataLocker
from backend.data.dl_thresholds import DLThresholdManager
from backend.models.alert_thresholds import AlertThreshold
import backend.sonic_backend_app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    patches = [
        "_seed_modifiers_if_empty",
        "_seed_wallets_if_empty",
        "_seed_thresholds_if_empty",
        "_seed_alerts_if_empty",
        "_ensure_travel_percent_threshold",
        "_seed_alert_config_if_empty",
    ]
    for name in patches:
        monkeypatch.setattr(DataLocker, name, lambda self: None)

    dl = DataLocker(str(tmp_path / "thr.db"))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    client = TestClient(app_module.app)
    yield client, dl
    dl.close()


def test_threshold_crud_flow(client):
    http, dl = client
    mgr = DLThresholdManager(dl.db)

    # list should start empty
    resp = http.get("/alert_thresholds/")
    assert resp.status_code == 200
    assert resp.json() == []

    t = AlertThreshold(
        id="t1",
        alert_type="TypeA",
        alert_class="ClassA",
        metric_key="metric",
        condition="ABOVE",
        low=1,
        medium=2,
        high=3,
        enabled=True,
        last_modified=datetime.now(timezone.utc).isoformat(),
    )

    resp = http.post("/alert_thresholds/", json=t.to_dict())
    assert resp.status_code == 201
    assert mgr.get_by_id("t1") is not None

    # update threshold
    resp = http.put("/alert_thresholds/t1", json={"low": 5})
    assert resp.status_code == 200
    assert mgr.get_by_id("t1").low == 5

    # delete threshold
    resp = http.delete("/alert_thresholds/t1")
    assert resp.status_code == 200
    assert mgr.get_by_id("t1") is None

    resp = http.get("/alert_thresholds/")
    assert resp.status_code == 200
    assert resp.json() == []
