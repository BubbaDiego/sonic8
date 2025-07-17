from __future__ import annotations

from enum import StrEnum, auto
from sqlalchemy.orm import DeclarativeBase

class Condition(StrEnum):
    ABOVE = auto()
    BELOW = auto()

class AlertLevel(StrEnum):
    NORMAL = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()

class NotificationType(StrEnum):
    SMS = auto()
    EMAIL = auto()
    WINDOWS = auto()
    PHONECALL = auto()

class Base(DeclarativeBase):
    pass
