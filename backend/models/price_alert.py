"""Price alert data models for Market Core."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class _DataModelMixin:
    """Utility mixin that provides ``dict`` and ``copy`` helpers for dataclasses."""

    def dict(self) -> Dict[str, Any]:
        return asdict(self)

    def copy(self, *, update: Optional[Dict[str, Any]] = None):  # type: ignore[override]
        return replace(self, **(update or {}))


class PriceAlertMode(str, Enum):
    MOVE_PERCENT = "move_percent"
    MOVE_ABSOLUTE = "move_absolute"
    PRICE_TARGET = "price_target"


class PriceAlertDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    ABOVE = "above"
    BELOW = "below"
    BOTH = "both"


class PriceAlertRecurrence(str, Enum):
    SINGLE = "single"
    RESET = "reset"
    LADDER = "ladder"


class PriceAlertStateEnum(str, Enum):
    OK = "OK"
    WARN = "WARN"
    BREACH = "BREACH"
    DISARMED = "DISARMED"


@dataclass
class PriceAlertConfig(_DataModelMixin):
    id: Optional[int] = None
    asset: str = ""
    name: Optional[str] = None
    enabled: bool = True
    mode: PriceAlertMode = PriceAlertMode.MOVE_PERCENT
    direction: PriceAlertDirection = PriceAlertDirection.BOTH
    threshold_value: float = 0.0
    original_threshold_value: Optional[float] = None
    recurrence: PriceAlertRecurrence = PriceAlertRecurrence.SINGLE
    cooldown_seconds: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PriceAlertState(_DataModelMixin):
    original_anchor_price: Optional[float] = None
    original_anchor_time: Optional[datetime] = None
    current_anchor_price: Optional[float] = None
    current_anchor_time: Optional[datetime] = None
    armed: bool = True
    fired_count: int = 0
    last_state: PriceAlertStateEnum = PriceAlertStateEnum.OK
    last_price: Optional[float] = None
    last_move_abs: Optional[float] = None
    last_move_pct: Optional[float] = None
    last_distance_to_target: Optional[float] = None
    last_proximity_ratio: Optional[float] = None
    last_evaluated_at: Optional[datetime] = None
    last_triggered_at: Optional[datetime] = None
    last_reset_at: Optional[datetime] = None


@dataclass
class PriceAlert(_DataModelMixin):
    config: PriceAlertConfig
    state: PriceAlertState = field(default_factory=PriceAlertState)

    def copy_with(
        self,
        *,
        config_updates: Optional[Dict[str, Any]] = None,
        state_updates: Optional[Dict[str, Any]] = None,
    ) -> "PriceAlert":
        cfg = self.config.copy(update=config_updates or {})
        st = self.state.copy(update=state_updates or {})
        return PriceAlert(config=cfg, state=st)


__all__ = [
    "PriceAlert",
    "PriceAlertConfig",
    "PriceAlertState",
    "PriceAlertMode",
    "PriceAlertDirection",
    "PriceAlertRecurrence",
    "PriceAlertStateEnum",
]
