from enum import Enum
from pydantic import BaseModel
from typing import Optional


class OrderSide(str, Enum):
    buy = "buy"
    sell = "sell"


class OrderType(str, Enum):
    market = "market"
    limit = "limit"


class OrderCreate(BaseModel):
    instrument: str
    side: OrderSide
    type: OrderType
    qty: str
    price: Optional[str] = None
    account_id: str
    client_ref: Optional[str] = None


class Order(BaseModel):
    id: str
    instrument: str
    side: OrderSide
    type: OrderType
    qty: str
    price: Optional[str] = None
    status: str = "open"
    account_id: str
