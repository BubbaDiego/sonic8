from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_create_order_invalid_price():
    payload = {
        "instrument": "BTC-PERP",
        "side": "buy",
        "type": "limit",
        "price": "-10",
        "qty": "0.10",
        "account_id": "acc_123",
    }
    r = client.post(
        "/orders",
        json=payload,
        headers={
            "Authorization": "Bearer dev-token",
            "Idempotency-Key": "test-001",
        },
    )
    assert r.status_code == 422
    assert r.json()["detail"]["error"]["code"] == "INVALID_PRICE"
