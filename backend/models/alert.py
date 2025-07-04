from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

try:
    from pydantic import BaseModel
    if not hasattr(BaseModel, "__fields__"):
        raise ImportError("stub")
except Exception:  # pragma: no cover - optional dependency
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def dict(self) -> dict:  # type: ignore[override]
            return self.__dict__

class Condition(str, Enum):
    ABOVE = "ABOVE"
    BELOW = "BELOW"

class NotificationType(str, Enum):
    SMS = "SMS"
    WINDOWS = "WINDOWS"
    EMAIL = "EMAIL"
    PHONECALL = "PHONECALL"

class AlertType(str, Enum):
    PriceThreshold = "PriceThreshold"
    Profit = "Profit"
    TravelPercentLiquid = "TravelPercentLiquid"
    TravelPercent = "TravelPercent"
    HeatIndex = "HeatIndex"
    DeathNail = "DeathNail"
    TotalValue = "TotalValue"
    TotalSize = "TotalSize"
    AvgLeverage = "AvgLeverage"
    AvgTravelPercent = "AvgTravelPercent"
    ValueToCollateralRatio = "ValueToCollateralRatio"
    TotalHeat = "TotalHeat"


class AlertLevel(str, Enum):
    NORMAL = "Normal"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class Alert(BaseModel):
    id: str
    description: str
    alert_class: str
    alert_type: str
    trigger_value: float
    evaluated_value: float | None = None
    condition: Condition
    level: AlertLevel = AlertLevel.NORMAL
    notification_type: NotificationType = NotificationType.SMS
    created_at: datetime
    position_reference_id: Optional[str] = None


class AlertLog(BaseModel):
    id: str
    alert_id: Optional[str] = None
    phase: Literal["CONFIG", "ENRICH", "EVAL", "NOTIFY", "ERROR"]
    level: Literal["DEBUG", "INFO", "WARN", "ERROR"]
    message: str
    payload: dict | None = None
    timestamp: datetime


from .alert_thresholds import AlertThreshold

__all__ = [
    "AlertType",
    "NotificationType",
    "Condition",
    "AlertLevel",
    "Alert",
    "AlertLog",
    "AlertThreshold",
]
