from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Sonic API")

class OrderCreate(BaseModel):
    instrument: str
    side: str
    type: str
    qty: str
    price: Optional[str] = None
    account_id: str
    client_ref: Optional[str] = None

class Order(BaseModel):
    id: str
    instrument: str
    side: str
    type: str
    qty: str
    price: Optional[str] = None
    status: str = "open"
    account_id: str

@app.post("/orders", response_model=Order)
def create_order(payload: OrderCreate, authorization: Optional[str] = Header(None), idempotency_key: Optional[str] = Header(None, convert_underscores=False)):
    if not authorization:
        raise HTTPException(status_code=401, detail={"error": {"code": "AUTH_REQUIRED", "message": "Missing bearer token"}})
    if not idempotency_key:
        raise HTTPException(status_code=400, detail={"error": {"code": "IDEMPOTENCY_REQUIRED", "message": "Provide Idempotency-Key"}})
    return Order(id="ord_001", **payload.model_dump())
