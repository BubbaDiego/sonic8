"""backend/data/dl_session.py

DLSessionManager – data‑layer helper for CRUD on the *sessions* table.
Mirrors the style of DLPortfolioManager but enforces **single active session**
semantics.

Public methods
--------------
start_session()        – archive current OPEN sessions and create a new one
get_active_session()   – return the OPEN session or None
update_session()       – partial update by id or on the active row
reset_session()        – zero out live metrics while keeping the row OPEN
close_session()        – mark the active row CLOSED
list_sessions()        – enumerate historical sessions (newest first)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Mapping, Any
from uuid import uuid4

from backend.core.logging import log
from backend.models.session import Session, SessionUpdate


class DLSessionManager:
    """Low‑level wrapper around the *sessions* SQLite table."""

    def __init__(self, db):
        self.db = db
        log.debug("DLSessionManager initialised", source="DLSessionManager")

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #
    def _row_to_session(self, row) -> Session:
        data = dict(row)
        # SQLite stores timestamps as text – convert back to datetime if needed
        for col in ("session_start_time", "last_modified"):
            if data.get(col) and isinstance(data[col], str):
                try:
                    data[col] = datetime.fromisoformat(data[col])
                except ValueError:
                    pass
        return Session(**data)

    def _execute(self, sql: str, params: tuple | dict = ()):
        cur = self.db.get_cursor()
        if cur is None:
            raise RuntimeError("DB unavailable in DLSessionManager")
        cur.execute(sql, params)
        return cur

    # ------------------------------------------------------------------ #
    # CRUD                                                               #
    # ------------------------------------------------------------------ #
    def start_session(
        self,
        start_value: float = 0.0,
        goal_value: float = 0.0,
        notes: str | None = None,
    ) -> Session:
        """Archive any OPEN session and create a fresh row."""

        cur = self._execute(
            "UPDATE sessions SET status='CLOSED', last_modified=? WHERE status='OPEN'",
            (datetime.utcnow().isoformat(),),
        )

        new_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        self._execute(
            """INSERT INTO sessions
                 (id, session_start_time, session_start_value,
                  session_goal_value, current_session_value,
                  session_performance_value, status, notes, last_modified)
                 VALUES (?, ?, ?, ?, 0, 0, 'OPEN', ?, ?)""",
            (
                new_id,
                now,
                start_value,
                goal_value,
                notes,
                now,
            ),
        )
        self.db.commit()
        return self.get_session_by_id(new_id)

    def get_session_by_id(self, sid: str) -> Optional[Session]:
        cur = self._execute("SELECT * FROM sessions WHERE id = ?", (sid,))
        row = cur.fetchone()
        return self._row_to_session(row) if row else None

    def get_active_session(self) -> Optional[Session]:
        cur = self._execute("SELECT * FROM sessions WHERE status='OPEN' LIMIT 1")
        row = cur.fetchone()
        return self._row_to_session(row) if row else None

    def list_sessions(self, limit: int | None = None) -> list[Session]:
        sql = "SELECT * FROM sessions ORDER BY session_start_time DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        cur = self._execute(sql)
        return [self._row_to_session(r) for r in cur.fetchall()]

    def update_session(
        self,
        sid: str | None,
        patch: SessionUpdate | Mapping[str, Any],
    ) -> Session | None:
        """Update `sid` or the OPEN session if sid is None."""

        if isinstance(patch, SessionUpdate):
            patch = patch.dict(exclude_unset=True)

        if not patch:
            return self.get_session_by_id(sid) if sid else self.get_active_session()

        if "last_modified" not in patch:
            patch["last_modified"] = datetime.utcnow().isoformat()

        fields = ", ".join(f"{k} = :{k}" for k in patch.keys())
        if sid is None:
            sql = f"UPDATE sessions SET {fields} WHERE status='OPEN'"
        else:
            sql = f"UPDATE sessions SET {fields} WHERE id = :sid"
            patch["sid"] = sid
        cur = self._execute(sql, patch)
        if cur.rowcount == 0 and sid is None:
            # No active session – create one with provided baseline fields
            new = self.start_session(
                start_value=patch.get("session_start_value", 0.0),
                goal_value=patch.get("session_goal_value", 0.0),
                notes=patch.get("notes"),
            )
            return self.update_session(new.id, patch)
        self.db.commit()
        return self.get_session_by_id(sid) if sid else self.get_active_session()

    def reset_session(self) -> Optional[Session]:
        """Set numeric metrics to zero but keep it OPEN."""

        open_session = self.get_active_session()
        if not open_session:
            return None

        patch = {
            "current_session_value": 0.0,
            "session_performance_value": 0.0,
            "session_start_time": datetime.utcnow().isoformat(),
            "session_start_value": 0.0,
        }
        return self.update_session(open_session.id, patch)

    def close_session(self) -> Optional[Session]:
        open_session = self.get_active_session()
        if not open_session:
            return None
        return self.update_session(open_session.id, {"status": "CLOSED"})
