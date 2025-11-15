"""Event log entries for price alerts."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from backend.models.price_alert import (
    PriceAlertDirection,
    PriceAlertMode,
    PriceAlertStateEnum,
)


class _DataModelMixin:
    def dict(self) -> Dict[str, Any]:
        return asdict(self)

    def copy(self, *, update: Optional[Dict[str, Any]] = None):  # type: ignore[override]
        return replace(self, **(update or {}))


class PriceAlertEventType(str, Enum):
    BREACH = "breach"
    WARN = "warn"
    RESET = "reset"
    INFO = "info"


@dataclass
class PriceAlertEvent(_DataModelMixin):
    id: Optional[str] = None
    alert_id: Optional[int] = None
    asset: Optional[str] = None
    event_type: PriceAlertEventType = PriceAlertEventType.INFO
    state_after: PriceAlertStateEnum = PriceAlertStateEnum.OK
    mode: Optional[PriceAlertMode] = None
    direction: Optional[PriceAlertDirection] = None
    price: Optional[float] = None
    anchor_price: Optional[float] = None
    movement_abs: Optional[float] = None
    movement_pct: Optional[float] = None
    threshold_value: Optional[float] = None
    distance_to_target: Optional[float] = None
    proximity_ratio: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    note: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


__all__ = ["PriceAlertEvent", "PriceAlertEventType"]
