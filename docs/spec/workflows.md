# Workflows

## Create Order
- **Trigger**: User submits trade.
- **Input**: [OrderCreate](../schemas/order_create.json)
- **Output**: [Order](../schemas/order.json)
- **Invariants**:
  - `Authorization` bearer token required.
  - `Idempotency-Key` header required.
  - `side` \in {`buy`, `sell`}.
  - `type` \in {`market`, `limit`}.
  - `qty` > 0 and within instrument limits.
- **Failure Modes**:
  - `AUTH_REQUIRED`
  - `IDEMPOTENCY_REQUIRED`
  - `VALIDATION_ENUM_SIDE`
  - `VALIDATION_ENUM_TYPE`
  - `VALIDATION_OUT_OF_RANGE`
  - `DOMAIN_NO_SUCH_ACCOUNT`
  - `RETRYABLE_PROVIDER_TIMEOUT`
- **Examples (FastAPI TestClient)**:
```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Success
payload = {
    "instrument": "BTC-PERP",
    "side": "buy",
    "type": "limit",
    "price": "62000.00",
    "qty": "0.10",
    "account_id": "acc_123"
}
res = client.post(
    "/orders",
    json=payload,
    headers={"Authorization": "Bearer token", "Idempotency-Key": "abc"},
)
assert res.status_code == 200

# Failure - missing idempotency key
res = client.post(
    "/orders",
    json=payload,
    headers={"Authorization": "Bearer token"},
)
assert res.status_code == 400
assert res.json()["error"]["code"] == "IDEMPOTENCY_REQUIRED"
```

## Adjust Collateral
- **Trigger**: Margin update requested.
- **Input**: [PositionAdjustRequest](../schemas/position_adjust_request.json)
- **Output**: [Position](../schemas/position.json)
- **Invariants**:
  - `Authorization` bearer token required.
  - `Idempotency-Key` header required.
  - `delta` \>= 0 and within collateral limits.
- **Failure Modes**:
  - `AUTH_REQUIRED`
  - `IDEMPOTENCY_REQUIRED`
  - `VALIDATION_NEGATIVE_DELTA`
  - `DOMAIN_POSITION_NOT_FOUND`
  - `DOMAIN_BELOW_MAINTENANCE`
- **Examples (FastAPI TestClient)**:
```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Success
ares = client.post(
    "/positions/pos_abc/adjust",
    json={"delta": 50},
    headers={"Authorization": "Bearer token", "Idempotency-Key": "xyz"},
)
assert ares.status_code == 200

# Failure - negative delta
ares = client.post(
    "/positions/pos_abc/adjust",
    json={"delta": -5},
    headers={"Authorization": "Bearer token", "Idempotency-Key": "xyz"},
)
assert ares.status_code == 400
assert ares.json()["error"]["code"] == "VALIDATION_NEGATIVE_DELTA"
```

## TP/SL Automation
- **Trigger**: Strategy signals exit.
- **Input**: [Strategy](../schemas/strategy.json)
- **Output**: [Order](../schemas/order.json)
- **Invariants**:
  - `Authorization` bearer token required.
  - `Idempotency-Key` header required.
  - Strategy must own the order.
  - `side` \in {`buy`, `sell`} and `type` \in {`market`, `limit`}.
- **Failure Modes**:
  - `AUTH_REQUIRED`
  - `IDEMPOTENCY_REQUIRED`
  - `DOMAIN_STRATEGY_NOT_OWNER`
  - `RETRYABLE_PROVIDER_TIMEOUT`
- **Examples (FastAPI TestClient)**:
```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Success (strategy closes position via order create)
res = client.post(
    "/orders",
    json={
        "instrument": "BTC-PERP",
        "side": "sell",
        "type": "market",
        "qty": "0.10",
        "account_id": "acc_123"
    },
    headers={"Authorization": "Bearer token", "Idempotency-Key": "tp1"},
)
assert res.status_code == 200

# Failure - missing auth
res = client.post(
    "/orders",
    json={"instrument": "BTC-PERP", "side": "sell", "type": "market", "qty": "0.10", "account_id": "acc_123"},
)
assert res.status_code == 401
assert res.json()["error"]["code"] == "AUTH_REQUIRED"
```


## Liquidation Alerts
- **Trigger**: Position approaches margin call.
- **Input**: [LiquidationAlertRequest](../schemas/liquidation_alert_request.json)
- **Output**: [Alert](../schemas/alert.json)
- **Invariants**:
  - `Authorization` bearer token required.
  - `Idempotency-Key` header required.
  - Position must exist.
- **Failure Modes**:
  - `AUTH_REQUIRED`
  - `IDEMPOTENCY_REQUIRED`
  - `DOMAIN_NO_SUCH_POSITION`
  - `RETRYABLE_PROVIDER_TIMEOUT`
- **Examples (FastAPI TestClient)**:
```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

# Success
res = client.post(
    "/alerts/liquidations",
    json={"position_id": "pos_abc"},
    headers={"Authorization": "Bearer token", "Idempotency-Key": "alrt1"},
)
assert res.status_code == 200

# Failure - missing auth
res = client.post(
    "/alerts/liquidations",
    json={"position_id": "pos_abc"},
)
assert res.status_code == 401
assert res.json()["error"]["code"] == "AUTH_REQUIRED"
```
