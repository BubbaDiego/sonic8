from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_create_order_happy_path():
    payload = {
        "instrument": "BTC-PERP",
        "side": "buy",
        "type": "limit",
        "price": "62000.00",
        "qty": "0.10",
        "account_id": "acc_123"
    }
    r = client.post("/orders", json=payload, headers={
        "Authorization": "Bearer dev-token",
        "Idempotency-Key": "golden-001"
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["instrument"] == "BTC-PERP"
    assert data["qty"] == "0.10"
