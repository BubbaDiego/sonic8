from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - fallback for docs / tools
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

        def model_dump(self, *_, **__):  # mimic minimal pydantic API
            return self.__dict__

        def dict(self, *args, **kwargs):  # compatibility shim
            return self.model_dump(*args, **kwargs)

    def Field(*args, **kwargs):  # type: ignore
        if "default_factory" in kwargs:
            return kwargs["default_factory"]()
        return kwargs.get("default", None)


class GoalMode(str, Enum):
    """How to interpret session_goal_value."""

    DELTA = "DELTA"  # goal = gain from session_start_value
    ABSOLUTE = "ABSOLUTE"  # goal = absolute portfolio value target


class _SessionBase(BaseModel):
    session_start_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the session began.",
    )
    session_start_value: float = Field(
        default=0.0, description="Portfolio value when the session started."
    )
    session_goal_value: float = Field(
        default=0.0, description="Target portfolio value or delta goal."
    )
    current_session_value: float = Field(
        default=0.0, description="Current session value (absolute or delta)."
    )
    session_performance_value: float = Field(
        default=0.0,
        description="Performance metric comparing against the start of the session.",
    )
    status: str = Field(default="OPEN", description="OPEN or CLOSED")
    notes: Optional[str] = Field(
        default=None, description="Free-form notes about the session."
    )
    # New metadata fields
    session_label: Optional[str] = Field(
        default=None,
        description="Human-friendly name for this session (e.g. 'London open scalps').",
    )
    goal_mode: GoalMode = Field(
        default=GoalMode.DELTA,
        description=(
            "How to interpret session_goal_value: "
            "DELTA = gain from start, ABSOLUTE = absolute portfolio target."
        ),
    )
    last_modified: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the last modification to the session row.",
    )


class SessionCreate(_SessionBase):
    """Payload for creating a session via API."""

    pass


class Session(_SessionBase):
    id: str


class SessionUpdate(BaseModel):
    """Partial update payload for sessions."""

    session_start_time: Optional[datetime] = None
    session_start_value: Optional[float] = None
    session_goal_value: Optional[float] = None
    current_session_value: Optional[float] = None
    session_performance_value: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    # New updatable fields
    session_label: Optional[str] = None
    goal_mode: Optional[GoalMode] = None
    last_modified: Optional[datetime] = None
