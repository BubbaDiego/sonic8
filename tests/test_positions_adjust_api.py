from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_adjust_negative_delta():
    r = client.post(
        "/positions/pos_123/adjust",
        json={"delta": -5},
        headers={
            "Authorization": "Bearer dev-token",
            "Idempotency-Key": "test-002",
        },
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "NEGATIVE_DELTA"


def test_adjust_excessive_delta():
    r = client.post(
        "/positions/pos_123/adjust",
        json={"delta": 1000},
        headers={
            "Authorization": "Bearer dev-token",
            "Idempotency-Key": "test-003",
        },
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "EXCESSIVE_DELTA"
