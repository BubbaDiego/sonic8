# API Index — Sonic API

## `/alerts/liquidations`

### POST /alerts/liquidations
*Create Liquidation Alert*

**Parameters**
- `authorization` (header, optional): 
- `idempotency-key` (header, optional): 

**Request Body**
- application/json → [LiquidationAlertRequest](../schemas/liquidation_alert_request.json)

**Responses**
- **200**: Successful Response
- **422**: Validation Error

## `/orders`

### POST /orders
*Create Order*

**Parameters**
- `authorization` (header, optional): 
- `idempotency-key` (header, optional): 

**Request Body**
- application/json → [OrderCreate](../schemas/order_create.json)

**Responses**
- **200**: Successful Response
- **422**: Validation Error

## `/positions/{position_id}/adjust`

### POST /positions/{position_id}/adjust
*Adjust Position*

**Parameters**
- `position_id` (path, required): string
- `authorization` (header, optional): 
- `idempotency-key` (header, optional): 

**Request Body**
- application/json → [PositionAdjustRequest](../schemas/position_adjust_request.json)

**Responses**
- **200**: Successful Response
- **422**: Validation Error
