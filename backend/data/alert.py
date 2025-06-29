from enum import Enum

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

__all__ = [
    "AlertType",
    "NotificationType",
    "Condition",
]
