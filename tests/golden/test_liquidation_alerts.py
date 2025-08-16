from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_liquidation_alert_minimum():
    payload = {"position_id": "pos_abc"}
    r = client.post(
        "/alerts/liquidations",
        json=payload,
        headers={
            "Authorization": "Bearer dev-token",
            "Idempotency-Key": "golden-003"
        },
    )
    assert r.status_code == 200
    assert r.json()["position_id"] == "pos_abc"
