from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_adjust_collateral_minimum_guardrail():
    r = client.post(
        "/positions/pos_abc/adjust",
        json={"delta": "50"},
        headers={
            "Authorization": "Bearer dev-token",
            "Idempotency-Key": "golden-002"
        },
    )
    assert r.status_code == 200
