from __future__ import annotations

from datetime import datetime, timezone
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


class AlertThreshold:
    def __init__(
        self,
        id: str,
        alert_type: str,
        alert_class: str,
        metric_key: str,
        condition: str,
        low: float,
        medium: float,
        high: float,
        enabled: bool = True,
        last_modified: str | None = None,
        low_notify: str = "",
        medium_notify: str = "",
        high_notify: str = "",
    ) -> None:
        self.id = id
        self.alert_type = alert_type
        self.alert_class = alert_class
        self.metric_key = metric_key
        self.condition = condition
        self.low = low
        self.medium = medium
        self.high = high
        self.enabled = enabled
        self.last_modified = (
            last_modified or datetime.now(timezone.utc).isoformat()
        )
        self.low_notify = low_notify
        self.medium_notify = medium_notify
        self.high_notify = high_notify

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "alert_class": self.alert_class,
            "metric_key": self.metric_key,
            "condition": self.condition,
            "low": self.low,
            "medium": self.medium,
            "high": self.high,
            "enabled": self.enabled,
            "last_modified": self.last_modified,
            "low_notify": self.low_notify,
            "medium_notify": self.medium_notify,
            "high_notify": self.high_notify,
        }

__all__ = [
    "AlertType",
    "NotificationType",
    "Condition",
    "AlertLevel",
    "Alert",
    "AlertLog",
    "AlertThreshold",
]
