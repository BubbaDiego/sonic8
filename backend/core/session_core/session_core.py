from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from backend.data.data_locker import DataLocker
from backend.data.dl_sessions import DLSessions
from .session_models import Session, SessionStatus


class SessionCore:
    """
    High-level session services for Sonic.

    All session CRUD should go through this class.
    """

    def __init__(self, dl: DataLocker) -> None:
        self._dl = dl
        self._store = DLSessions(dl)

    # ------------------------------------------------------------------ #
    # Listing / lookup                                                   #
    # ------------------------------------------------------------------ #

    def list_sessions(self) -> List[Session]:
        return self._store.list_sessions()

    def list_active_sessions(self) -> List[Session]:
        return [s for s in self._store.list_sessions() if s.status is SessionStatus.ACTIVE]

    def get_session(self, sid: str) -> Optional[Session]:
        return self._store.get_session(sid)

    # ------------------------------------------------------------------ #
    # CRUD                                                               #
    # ------------------------------------------------------------------ #

    def create_session(
        self,
        *,
        primary_wallet_name: str,
        name: Optional[str] = None,
        goal: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> Session:
        sid = uuid.uuid4().hex[:8]
        session = Session(
            sid=sid,
            name=name or f"{primary_wallet_name}-{sid}",
            primary_wallet_name=primary_wallet_name,
            goal=goal,
            tags=tags or [],
            notes=notes,
        )
        return self._store.upsert_session(session)

    def update_session(
        self,
        sid: str,
        *,
        name: Optional[str] = None,
        goal: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        status: Optional[SessionStatus] = None,
    ) -> Optional[Session]:
        session = self._store.get_session(sid)
        if not session:
            return None

        changed = False

        if name is not None and name != session.name:
            session.name = name
            changed = True

        if goal is not None and goal != session.goal:
            session.goal = goal
            changed = True

        if tags is not None and tags != session.tags:
            session.tags = tags
            changed = True

        if notes is not None and notes != session.notes:
            session.notes = notes
            changed = True

        if status is not None and status != session.status:
            session.status = status
            if status is SessionStatus.CLOSED and session.closed_at is None:
                session.closed_at = datetime.utcnow()
            changed = True

        if not changed:
            return session

        session.touch()
        return self._store.upsert_session(session)

    def close_session(self, sid: str) -> Optional[Session]:
        return self.update_session(sid, status=SessionStatus.CLOSED)

    def delete_session(self, sid: str) -> bool:
        return self._store.delete_session(sid)

    def rename_session(self, sid: str, new_name: str) -> Optional[Session]:
        return self.update_session(sid, name=new_name)
