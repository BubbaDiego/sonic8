# backend/models/position.py
"""Position data models."""

from datetime import datetime
from typing import Optional

try:
    from pydantic import BaseModel, Field, constr, ConfigDict
    if not hasattr(BaseModel, "__fields__"):
        raise ImportError("stub")
except Exception:  # pragma: no cover - fallback when pydantic isn't available
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self) -> dict:  # type: ignore
            return self.__dict__

        # pydantic v1 compatibility used in tests
        def dict(self) -> dict:  # type: ignore[override]
            return self.__dict__

    def Field(default=None, **_):  # type: ignore
        return default

    def constr(*_, **__):  # type: ignore
        return str

    ConfigDict = dict  # type: ignore

class Position(BaseModel):
    id: constr(min_length=1)
    asset_type: str
    position_type: str
    entry_price: float
    size: float
    leverage: float
    wallet_name: str
    last_updated: Optional[datetime] = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class PositionDB(BaseModel):
    """Full representation of a row in the ``positions`` table."""

    id: constr(min_length=1)
    asset_type: str = "UNKNOWN"
    position_type: str = "LONG"
    entry_price: float = 0.0
    liquidation_price: float = 0.0
    travel_percent: float = 0.0
    value: float = 0.0
    collateral: float = 0.0
    size: float = 0.0
    leverage: float = 1.0
    wallet_name: str = "Unspecified"
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    alert_reference_id: Optional[str] = None
    hedge_buddy_id: Optional[str] = None
    current_price: float = 0.0
    liquidation_distance: float = 0.0
    heat_index: float = 0.0
    current_heat_index: float = 0.0
    pnl_after_fees_usd: float = 0.0
    status: str = "ACTIVE"
    stale: int = 0

    model_config = ConfigDict(from_attributes=True)


__all__ = ["Position", "PositionDB"]
