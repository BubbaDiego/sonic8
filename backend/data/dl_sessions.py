from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import List, Optional

from backend.data.data_locker import DataLocker
from backend.models.session import (
    Session,
    SessionCreate,
    SessionStatus,
    SessionUpdate,
)


class SessionStore:
    """
    DataLocker facade for CRUD access to trading sessions.

    This should follow the same conventions as dl_portfolio, dl_positions, etc.
    """

    def __init__(self, dl: DataLocker) -> None:
        self._dl = dl

    def _row_to_session(self, row) -> Session:
        data = dict(row)
        for ts_field in (
            "created_at",
            "updated_at",
            "started_at",
            "ended_at",
            "session_start_time",
            "last_modified",
        ):
            value = data.get(ts_field)
            if isinstance(value, str):
                try:
                    data[ts_field] = datetime.fromisoformat(value)
                except ValueError:
                    pass
        status = data.get("status")
        if status is not None:
            try:
                data["status"] = SessionStatus(status)
            except ValueError:
                pass
        return Session(**data)

    def _get_cursor(self):
        return self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None

    # Read operations -----------------------------------------------------------

    def list_sessions(
        self,
        wallet_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
    ) -> List[Session]:
        """
        Return all sessions, optionally filtered by wallet_id and/or status.

        Results should be ordered by created_at DESC (most recent first).
        """
        cursor = self._get_cursor()
        if cursor is None:
            return []

        sql = "SELECT * FROM sessions"
        params = []
        clauses = []

        if wallet_id is not None:
            clauses.append("wallet_id = ?")
            params.append(wallet_id)

        if status is not None:
            clauses.append("status = ?")
            params.append(status.value if isinstance(status, SessionStatus) else status)

        if clauses:
            sql += " WHERE " + " AND ".join(clauses)

        sql += " ORDER BY created_at DESC"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [self._row_to_session(r) for r in rows]

    def get_session(self, session_id: int) -> Optional[Session]:
        """Return a single Session by ID, or None if it does not exist."""
        cursor = self._get_cursor()
        if cursor is None:
            return None
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return self._row_to_session(row) if row else None

    # Write operations ----------------------------------------------------------

    def create_session(self, payload: SessionCreate) -> Session:
        """
        Insert a new row into the sessions table and return the hydrated Session.
        """
        cursor = self._get_cursor()
        if cursor is None:
            raise RuntimeError("Database unavailable for creating session")

        now = datetime.utcnow().isoformat()
        cursor.execute(
            """
            INSERT INTO sessions (
                name,
                wallet_id,
                status,
                goal_label,
                goal_description,
                target_return_pct,
                max_drawdown_pct,
                created_at,
                updated_at,
                started_at,
                ended_at,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.wallet_id,
                SessionStatus.ACTIVE.value,
                payload.goal_label,
                payload.goal_description,
                payload.target_return_pct,
                payload.max_drawdown_pct,
                now,
                now,
                None,
                None,
                payload.notes,
            ),
        )
        self._dl.db.commit()
        session_id = cursor.lastrowid
        session = self.get_session(int(session_id)) if session_id is not None else None
        if session is None:
            return Session(
                id=int(session_id or 0),
                name=payload.name,
                wallet_id=payload.wallet_id,
                goal_label=payload.goal_label,
                goal_description=payload.goal_description,
                target_return_pct=payload.target_return_pct,
                max_drawdown_pct=payload.max_drawdown_pct,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
                notes=payload.notes,
            )
        return session

    def update_session(self, session_id: int, patch: SessionUpdate) -> Optional[Session]:
        """
        Apply a partial update to the given session. If the session does not
        exist, return None instead of raising.
        """
        cursor = self._get_cursor()
        if cursor is None:
            return None

        current = self.get_session(session_id)
        if current is None:
            return None

        patch_dict = {k: v for k, v in asdict(patch).items() if v is not None}
        if not patch_dict:
            return current

        patch_dict["updated_at"] = datetime.utcnow().isoformat()

        columns = ", ".join(f"{k} = ?" for k in patch_dict.keys())
        params = list(patch_dict.values()) + [session_id]

        cursor.execute(
            f"UPDATE sessions SET {columns} WHERE id = ?",
            params,
        )
        self._dl.db.commit()
        return self.get_session(session_id)

    def delete_session(self, session_id: int) -> bool:
        """
        Delete a session by ID.

        Returns True if a row was deleted, False if no such session existed.
        """
        cursor = self._get_cursor()
        if cursor is None:
            return False
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self._dl.db.commit()
        return cursor.rowcount > 0


__all__ = ["SessionStore"]
