from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SessionStatus(str, Enum):
    """Lifecycle state for a trading session."""

    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


@dataclass
class Session:
    """
    Canonical in-memory representation of a Sonic session.

    - `sid` is a short, stable identifier (string).
    - `primary_wallet_name` is the main wallet this session is associated with.
    - `wallet_names` allows multiple wallets to participate in one session.
    """

    sid: str  # primary key (string id, not DB integer)
    name: str

    primary_wallet_name: str
    wallet_names: List[str] = field(default_factory=list)

    status: SessionStatus = SessionStatus.ACTIVE

    # human intent / description
    goal: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    # timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None

    # overall metrics for the session (loose schema; interpreted by callers)
    metrics: Dict[str, Any] = field(default_factory=dict)

    # per-wallet metrics; key = wallet_name
    wallet_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def touch(self) -> None:
        """Update the 'updated_at' timestamp to now."""

        self.updated_at = datetime.utcnow()
