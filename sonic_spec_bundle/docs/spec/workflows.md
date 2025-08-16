# Workflows

> Each workflow = trigger(s), inputs, outputs, invariants, failure modes, and a tiny E2E example.

## Create Order
**Triggers:** UI button, strategy signal, CLI script.  
**Input:** `OrderCreate` (see `schemas/order_create.json`).  
**Output:** `Order` (see `schemas/order.json`).  
**Invariants:**
- Orders must reference a valid Account.
- Price/qty validated against instrument constraints.
- Idempotency key required from UI/strategy.
**Failure Modes:**
- `VALIDATION_OUT_OF_RANGE` (qty/price invalid)
- `DOMAIN_NO_SUCH_ACCOUNT`
- `RETRYABLE_PROVIDER_TIMEOUT`
**Example (HTTP):**
```http
POST /orders
Idempotency-Key: 07f3c3b3-1d6a-4a73-95c9-f0f21c6f6a8f
{
  "instrument": "BTC-PERP",
  "side": "buy",
  "type": "limit",
  "price": "62000.00",
  "qty": "0.10",
  "account_id": "acc_123"
}
```

## Update Position Collateral
**Triggers:** Risk monitor or manual UI action.  
**Input:** `PositionAdjust` (see `schemas/position_adjust.json`).  
**Output:** `Position` updated snapshot.  
**Invariants:**
- Cannot reduce below maintenance requirement.
- Emits `event=position.adjusted` with `correlation_id`.
**Example (Core call):**
```python
from core.use_cases.position import adjust_collateral
pos = adjust_collateral(position_id="pos_abc", delta=50.0, actor="ui")
```

## Emit Alert
**Triggers:** Threshold crossed.  
**Input:** `AlertCreate` (`schemas/alert_create.json`).  
**Outputs:** Notification fan-out via `infra/alerts/*`.  
**Invariants:** Single delivery attempt + DLQ on failure.
