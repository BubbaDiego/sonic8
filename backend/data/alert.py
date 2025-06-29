from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel

class Condition(str, Enum):
    ABOVE = "ABOVE"
    BELOW = "BELOW"

class NotificationType(str, Enum):
    SMS = "SMS"
    WINDOWS = "WINDOWS"

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

__all__ = [
    "AlertType",
    "NotificationType",
    "Condition",
    "AlertLevel",
    "Alert",
    "AlertLog",
]
