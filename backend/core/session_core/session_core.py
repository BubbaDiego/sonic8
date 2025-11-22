from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from backend.data.data_locker import DataLocker
from backend.data.dl_sessions import DLSessions
from .session_models import Session, SessionStatus


class SessionCore:
    """
    High-level session domain services.

    All reads/writes of session records should go through this core
    so we have a single place to evolve the model and DB schema.
    """

    def __init__(self, dl: DataLocker) -> None:
        self._dl = dl
        self._store = DLSessions(dl)

    # --- basic listing / lookup ------------------------------------------

    def list_sessions(self) -> List[Session]:
        return self._store.list_sessions()

    def get_session(self, sid: str) -> Optional[Session]:
        return self._store.get_session(sid)

    def list_active_sessions(self) -> List[Session]:
        """
        Convenience wrapper returning only ACTIVE sessions.
        """
        all_sessions = self._store.list_sessions()
        return [s for s in all_sessions if s.status is SessionStatus.ACTIVE]

    # --- creation / update / delete --------------------------------------

    def create_session(
        self,
        *,
        primary_wallet_name: str,
        name: Optional[str] = None,
        goal: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> Session:
        """
        Create a new ACTIVE session bound to a primary wallet.
        """
        sid = uuid.uuid4().hex[:8]
        session = Session(
            sid=sid,
            name=name or f"session-{sid}",
            primary_wallet_name=primary_wallet_name,
            wallet_names=[primary_wallet_name],
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
                # closed now
                from datetime import datetime as _dt

                session.closed_at = _dt.utcnow()
            changed = True

        if not changed:
            return session

        session.touch()
        return self._store.upsert_session(session)

    def rename_session(self, sid: str, new_name: str) -> Optional[Session]:
        """
        Convenience helper to change a session's name.
        """
        return self.update_session(sid, name=new_name)

    def close_session(self, sid: str) -> Optional[Session]:
        """
        Convenience helper: mark the session CLOSED and set closed_at.
        """
        return self.update_session(sid, status=SessionStatus.CLOSED)

    def delete_session(self, sid: str) -> bool:
        return self._store.delete_session(sid)

    # --- wallet membership -----------------------------------------------

    def attach_wallet(self, sid: str, wallet_name: str) -> Optional[Session]:
        session = self._store.get_session(sid)
        if not session:
            return None
        if wallet_name not in session.wallet_names:
            session.wallet_names.append(wallet_name)
            session.touch()
            session = self._store.upsert_session(session)
        return session

    def detach_wallet(self, sid: str, wallet_name: str) -> Optional[Session]:
        session = self._store.get_session(sid)
        if not session:
            return None
        if wallet_name in session.wallet_names and wallet_name != session.primary_wallet_name:
            session.wallet_names.remove(wallet_name)
            session.touch()
            session = self._store.upsert_session(session)
        return session

    # --- metrics plumbing -------------------------------------------------

    def update_metric(
        self,
        sid: str,
        key: str,
        value: Any,
        *,
        wallet_name: Optional[str] = None,
        accumulate: bool = False,
    ) -> Optional[Session]:
        """
        Update a metric at the session level or per-wallet level.

        If `wallet_name` is provided, metric is stored under
        session.wallet_metrics[wallet_name][key]. Otherwise stored under
        session.metrics[key].

        If accumulate=True and the existing value is numeric, we add to it;
        otherwise we just overwrite.
        """
        session = self._store.get_session(sid)
        if not session:
            return None

        if wallet_name:
            if wallet_name not in session.wallet_metrics:
                session.wallet_metrics[wallet_name] = {}
            bucket: Dict[str, Any] = session.wallet_metrics[wallet_name]
        else:
            bucket = session.metrics

        if accumulate and key in bucket and isinstance(bucket[key], (int, float)) and isinstance(value, (int, float)):
            bucket[key] = bucket[key] + value
        else:
            bucket[key] = value

        session.touch()
        return self._store.upsert_session(session)

    def get_active_sessions(self) -> List[Session]:
        """
        Convenience filter for callers that only care about active sessions.
        """
        return [s for s in self._store.list_sessions() if s.status is SessionStatus.ACTIVE]
