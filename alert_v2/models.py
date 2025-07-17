
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict, PositiveFloat
from sqlalchemy import DateTime, Float, String, Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from alert_common import Condition, AlertLevel, NotificationType, Base

# ------------------------------------------------------------------
# 1. Domain enums (see alert_common)
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# 3. ORM tables
# ------------------------------------------------------------------
class AlertConfigTbl(Base):
    __tablename__ = "alert_config"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    description: Mapped[str] = mapped_column(String, default="")
    alert_type: Mapped[str] = mapped_column(String)
    alert_class: Mapped[str] = mapped_column(String)
    trigger_value: Mapped[float] = mapped_column(Float)
    condition: Mapped[Condition] = mapped_column(Enum(Condition))
    notification_type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), default=NotificationType.SMS)
    position_reference_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # one‑to‑one relationship
    state: Mapped["AlertStateTbl"] = relationship(back_populates="config", uselist=False, cascade="all, delete-orphan")

class AlertStateTbl(Base):
    __tablename__ = "alert_state"
    alert_id: Mapped[str] = mapped_column(ForeignKey("alert_config.id"), primary_key=True)
    evaluated_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    level: Mapped[AlertLevel] = mapped_column(Enum(AlertLevel), default=AlertLevel.NORMAL)
    last_triggered: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    snoozed_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    config: Mapped[AlertConfigTbl] = relationship(back_populates="state")

class ThresholdTbl(Base):
    __tablename__ = "alert_threshold"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    alert_type: Mapped[str] = mapped_column(String)
    alert_class: Mapped[str] = mapped_column(String)
    metric_key: Mapped[str] = mapped_column(String)
    condition: Mapped[Condition] = mapped_column(Enum(Condition))
    low: Mapped[float] = mapped_column(Float)
    medium: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_modified: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AlertLogTbl(Base):
    __tablename__ = "alert_log"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    alert_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("alert_config.id"), nullable=True)
    phase: Mapped[str] = mapped_column(String)
    level: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)
    payload: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# ------------------------------------------------------------------
# 4. Pydantic models
# ------------------------------------------------------------------
class AlertConfig(BaseModel):
    id: str
    description: str = ""
    alert_type: str
    alert_class: str
    trigger_value: PositiveFloat
    condition: Condition
    notification_type: NotificationType = NotificationType.SMS
    position_reference_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(frozen=True)

class AlertState(BaseModel):
    alert_id: str
    evaluated_value: Optional[float] = None
    level: AlertLevel = AlertLevel.NORMAL
    last_triggered: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None

class Threshold(BaseModel):
    id: str
    alert_type: str
    alert_class: str
    metric_key: str
    condition: Condition
    low: PositiveFloat
    medium: PositiveFloat
    high: PositiveFloat
    enabled: bool = True
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    model_config = ConfigDict(frozen=True)

class AlertLog(BaseModel):
    id: str
    alert_id: Optional[str] = None
    phase: str
    level: str
    message: str
    payload: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
