from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


@dataclass
class Session:
    """
    Domain model for Sonic sessions.

    `sid` is a string identifier (e.g. short UUID).
    """

    sid: str
    name: str
    primary_wallet_name: str

    status: SessionStatus = SessionStatus.ACTIVE

    goal: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()
