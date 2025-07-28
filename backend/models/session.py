"""backend/models/session.py

Pydantic schemas for trading *Session* objects.
A *Session* represents the **live performance tracking window**
that the PortfolioSessionCard and related UI widgets display.

You normally have **one OPEN session at a time**.  When starting
a new session, the previous one is marked CLOSED (soft‑archived).
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

try:
    from pydantic import BaseModel, Field, ConfigDict
except ImportError:  # pragma: no cover – for stubbed environments
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def dict(self):
            return self.__dict__

    def Field(default=None, **_):  # type: ignore
        return default

    ConfigDict = dict  # type: ignore


# --------------------------------------------------------------------------- #
# Base mixin with common attributes                                           #
# --------------------------------------------------------------------------- #
class _SessionBase(BaseModel):
    """Common fields shared by all Session schemas."""

    session_start_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC time the session began",
    )
    session_start_value: float = Field(
        0.0, description="Portfolio value when the session started"
    )
    session_goal_value: float = Field(
        0.0, description="Target value you want to hit before closing"
    )
    current_session_value: float = Field(
        0.0, description="Current Δ (value ‑ start_value)"
    )
    session_performance_value: float = Field(
        0.0,
        description="P&L compared to *start* (includes realised + unrealised)",
    )
    status: str = Field("OPEN", description="OPEN or CLOSED")
    notes: Optional[str] = Field(None, description="Free‑form notes about the session")


class Session(_SessionBase):
    """Represents the **persisted row** inside the *sessions* table."""

    id: str = Field(
        default_factory=lambda: str(uuid4()), description="Primary key"
    )
    last_modified: datetime = Field(
        default_factory=datetime.utcnow,
        description="Auto‑updated timestamp whenever the row mutates",
    )

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- #
# Helper schemas for request / response payloads                              #
# --------------------------------------------------------------------------- #
class SessionCreate(_SessionBase):
    """Payload for POST /session (omit id + last_modified)."""

    pass


class SessionUpdate(BaseModel):
    """PATCH‑style payload; every field is optional."""

    session_start_time: Optional[datetime] = None
    session_start_value: Optional[float] = None
    session_goal_value: Optional[float] = None
    current_session_value: Optional[float] = None
    session_performance_value: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        extra = "forbid"
