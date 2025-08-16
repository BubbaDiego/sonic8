# Workflows

## Create Order
- **Trigger**: User submits trade.
- **Input**: [OrderCreate](../schemas/order.json)
- **Output**: [Order](../schemas/order.json)
- **Invariants**: `qty` must be positive.
- **Failure Modes**: `AUTH_REQUIRED`, `IDEMPOTENCY_REQUIRED`.
- **Example**: See [tests/golden/test_orders_create.py](../../tests/golden/test_orders_create.py).

## Adjust Collateral
- **Trigger**: Margin update requested.
- **Input**: [PositionAdjustRequest](../schemas/position.json)
- **Output**: [Position](../schemas/position.json)
- **Invariants**: `delta` non-negative.
- **Failure Modes**: `AUTH_REQUIRED`, `NEGATIVE_DELTA`.
- **Example**: See [tests/golden/test_positions_adjust.py](../../tests/golden/test_positions_adjust.py).

## TP/SL Automation
- **Trigger**: Strategy signals exit.
- **Input**: [Strategy](../schemas/strategy.json)
- **Output**: [Order](../schemas/order.json)
- **Invariants**: Strategy must own the order.
- **Failure Modes**: `AUTH_REQUIRED`.
- **Example**: Not yet implemented.

## Liquidation Alerts
- **Trigger**: Position approaches margin call.
- **Input**: [LiquidationAlertRequest](../schemas/alert.json)
- **Output**: [Alert](../schemas/alert.json)
- **Invariants**: Position must exist.
- **Failure Modes**: `AUTH_REQUIRED`.
- **Example**: See [tests/golden/test_liquidation_alerts.py](../../tests/golden/test_liquidation_alerts.py).
