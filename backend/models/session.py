from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SessionStatus(str, Enum):
    """
    Lifecycle of a trading session.

    - active: the session is currently in use
    - paused: temporarily inactive, may be resumed
    - completed: finished successfully (hit goal, etc.)
    - archived: historical / no longer relevant
    """

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class GoalMode(str, Enum):
    """Legacy goal interpretation retained for backward compatibility."""

    DELTA = "DELTA"
    ABSOLUTE = "ABSOLUTE"


@dataclass
class Session:
    """
    Canonical in-memory representation of a single trading session.

    `id` matches the primary key in the sessions table.
    """

    id: int
    name: str
    wallet_id: str
    status: SessionStatus = SessionStatus.ACTIVE

    # Goal / intent metadata
    goal_label: Optional[str] = None  # short “headline” for the goal
    goal_description: Optional[str] = None
    target_return_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    # Free-form notes
    notes: Optional[str] = None

    # Legacy/session metrics for compatibility with existing DLSessionManager
    session_start_time: Optional[datetime] = None
    session_start_value: Optional[float] = None
    session_goal_value: Optional[float] = None
    current_session_value: Optional[float] = None
    session_performance_value: Optional[float] = None
    session_label: Optional[str] = None
    goal_mode: Optional[GoalMode] = None
    last_modified: Optional[datetime] = None


@dataclass
class SessionCreate:
    """
    Payload used when creating a brand-new session.
    """

    name: str
    wallet_id: str

    goal_label: Optional[str] = None
    goal_description: Optional[str] = None
    target_return_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class SessionUpdate:
    """
    Partial update payload. All fields are optional.
    """

    name: Optional[str] = None
    wallet_id: Optional[str] = None
    status: Optional[SessionStatus] = None

    goal_label: Optional[str] = None
    goal_description: Optional[str] = None
    target_return_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None

    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    notes: Optional[str] = None

    # Legacy session fields
    session_start_time: Optional[datetime] = None
    session_start_value: Optional[float] = None
    session_goal_value: Optional[float] = None
    current_session_value: Optional[float] = None
    session_performance_value: Optional[float] = None
    session_label: Optional[str] = None
    goal_mode: Optional[GoalMode] = None
    last_modified: Optional[datetime] = None


__all__ = ["SessionStatus", "Session", "SessionCreate", "SessionUpdate", "GoalMode"]
