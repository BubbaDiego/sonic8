from fastapi import FastAPI, Header, HTTPException
from typing import Optional

from api.models import (
    Order,
    OrderCreate,
    Position,
    PositionAdjustRequest,
    Alert,
    LiquidationAlertRequest,
)

app = FastAPI(title="Sonic API")


@app.post("/orders", response_model=Order)
def create_order(
    payload: OrderCreate,
    authorization: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail={"error": {"code": "AUTH_REQUIRED", "message": "Missing bearer token"}})
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"error": {"code": "IDEMPOTENCY_REQUIRED", "message": "Provide Idempotency-Key"}})
    return Order(id="ord_001", **payload.model_dump())


@app.post("/positions/{position_id}/adjust", response_model=Position)
def adjust_position(
    position_id: str,
    payload: PositionAdjustRequest,
    authorization: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail={"error": {"code": "AUTH_REQUIRED", "message": "Missing bearer token"}})
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"error": {"code": "IDEMPOTENCY_REQUIRED", "message": "Provide Idempotency-Key"}})
    try:
        delta_val = int(payload.delta)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_DELTA", "message": "Delta must be numeric"}})
    if delta_val < 0:
        raise HTTPException(status_code=400, detail={"error": {"code": "NEGATIVE_DELTA", "message": "Delta must be positive"}})
    return Position(id=position_id, instrument="BTC-PERP", qty=payload.delta, account_id="acc_123")


@app.post("/alerts/liquidations", response_model=Alert)
def create_liquidation_alert(
    payload: LiquidationAlertRequest,
    authorization: Optional[str] = Header(None),
    idempotency_key: Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail={"error": {"code": "AUTH_REQUIRED", "message": "Missing bearer token"}})
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"error": {"code": "IDEMPOTENCY_REQUIRED", "message": "Provide Idempotency-Key"}})
    return Alert(id="alrt_001", position_id=payload.position_id)
