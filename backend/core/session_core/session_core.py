from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from backend.data.data_locker import DataLocker
from backend.data.dl_sessions import SessionStore
from backend.models.session import (
    Session,
    SessionCreate,
    SessionStatus,
    SessionUpdate,
)


class SessionCore:
    """
    Domain services for managing trading sessions.

    This core should be the *only* place higher layers (console, API routes)
    talk to for session CRUD and related queries.
    """

    def __init__(self, dl: DataLocker) -> None:
        self._dl = dl
        self._store = SessionStore(dl)

    # ---- CRUD surface ---------------------------------------------------------

    def list_sessions(
        self,
        wallet_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
    ) -> List[Session]:
        """
        Convenience wrapper around SessionStore.list_sessions.
        """
        return self._store.list_sessions(wallet_id=wallet_id, status=status)

    def get_session(self, session_id: int) -> Optional[Session]:
        return self._store.get_session(session_id)

    def create_session(
        self,
        wallet_id: str,
        name: str,
        *,
        goal_label: Optional[str] = None,
        goal_description: Optional[str] = None,
        target_return_pct: Optional[float] = None,
        max_drawdown_pct: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Session:
        """
        Create and persist a new session associated with a specific wallet_id.
        """
        payload = SessionCreate(
            name=name,
            wallet_id=wallet_id,
            goal_label=goal_label,
            goal_description=goal_description,
            target_return_pct=target_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            notes=notes,
        )
        return self._store.create_session(payload)

    def update_session(
        self,
        session_id: int,
        *,
        name: Optional[str] = None,
        wallet_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        goal_label: Optional[str] = None,
        goal_description: Optional[str] = None,
        target_return_pct: Optional[float] = None,
        max_drawdown_pct: Optional[float] = None,
        started_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> Optional[Session]:
        """
        Partially update a session. Fields left as None are not modified.
        """
        patch = SessionUpdate(
            name=name,
            wallet_id=wallet_id,
            status=status,
            goal_label=goal_label,
            goal_description=goal_description,
            target_return_pct=target_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            started_at=started_at,
            ended_at=ended_at,
            notes=notes,
        )
        return self._store.update_session(session_id, patch)

    def delete_session(self, session_id: int) -> bool:
        """
        Delete a session by ID.

        This is a hard delete for now; if we later want soft deletes, we can
        change the implementation to set status=archived instead.
        """
        return self._store.delete_session(session_id)

    # ---- convenience helpers --------------------------------------------------

    def get_active_sessions_for_wallet(self, wallet_id: str) -> List[Session]:
        """
        Helper for UI / monitoring.

        Returns all 'active' sessions tied to the given wallet_id, ordered
        consistently with SessionStore.list_sessions.
        """
        return self._store.list_sessions(
            wallet_id=wallet_id,
            status=SessionStatus.ACTIVE,
        )
