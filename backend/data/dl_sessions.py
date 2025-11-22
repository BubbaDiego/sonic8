from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from backend.data.data_locker import DataLocker
from backend.core.session_core.session_models import Session, SessionStatus


class DLSessions:
    """
    DataLocker facade for the 'sessions' table.

    The underlying table schema should be:

        CREATE TABLE IF NOT EXISTS sessions (
            sid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            primary_wallet_name TEXT NOT NULL,
            wallet_names TEXT NOT NULL,       -- JSON array of strings
            status TEXT NOT NULL,             -- one of SessionStatus values
            goal TEXT,
            tags TEXT NOT NULL,               -- JSON array of strings
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            closed_at TEXT,
            metrics TEXT NOT NULL,            -- JSON object
            wallet_metrics TEXT NOT NULL      -- JSON object
        );

    All timestamps are stored as ISO-8601 strings (UTC).
    """

    def __init__(self, dl: DataLocker) -> None:
        self._dl = dl
        self._ensure_table()

    # --- schema bootstrap -------------------------------------------------

    def _ensure_table(self) -> None:
        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                sid TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                primary_wallet_name TEXT NOT NULL,
                wallet_names TEXT NOT NULL,
                status TEXT NOT NULL,
                goal TEXT,
                tags TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                closed_at TEXT,
                metrics TEXT NOT NULL,
                wallet_metrics TEXT NOT NULL
            );
            """
        )
        self._dl.db.commit()

    # --- helpers for (de)serialization -----------------------------------

    def _row_to_session(self, row: dict) -> Session:
        data = dict(row)
        for ts_field in ("created_at", "updated_at", "closed_at"):
            value = data.get(ts_field)
            if value:
                try:
                    data[ts_field] = datetime.fromisoformat(value)
                except Exception:
                    pass

        try:
            data["status"] = SessionStatus(data["status"])
        except Exception:
            data["status"] = SessionStatus.ACTIVE

        for json_field in ("wallet_names", "tags", "metrics", "wallet_metrics"):
            raw_value = data.get(json_field)
            if isinstance(raw_value, str):
                try:
                    data[json_field] = json.loads(raw_value)
                except Exception:
                    data[json_field] = [] if json_field in ("wallet_names", "tags") else {}

        return Session(**data)

    def _session_to_row(self, session: Session) -> dict:
        return {
            "sid": session.sid,
            "name": session.name,
            "primary_wallet_name": session.primary_wallet_name,
            "wallet_names": json.dumps(session.wallet_names),
            "status": session.status.value,
            "goal": session.goal,
            "tags": json.dumps(session.tags),
            "notes": session.notes,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "closed_at": session.closed_at.isoformat() if session.closed_at else None,
            "metrics": json.dumps(session.metrics),
            "wallet_metrics": json.dumps(session.wallet_metrics),
        }

    # --- CRUD API ---------------------------------------------------------

    def list_sessions(self) -> List[Session]:
        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return []

        cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        rows = cursor.fetchall() or []
        return [self._row_to_session(row) for row in rows]

    def get_session(self, sid: str) -> Optional[Session]:
        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return None
        cursor.execute("SELECT * FROM sessions WHERE sid = ?", (sid,))
        row = cursor.fetchone()
        return self._row_to_session(row) if row else None

    def upsert_session(self, session: Session) -> Session:
        """
        Insert or replace a session row, based on session.sid.
        """

        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return session

        row = self._session_to_row(session)
        cursor.execute(
            """
            INSERT OR REPLACE INTO sessions (
                sid, name, primary_wallet_name, wallet_names, status,
                goal, tags, notes, created_at, updated_at, closed_at,
                metrics, wallet_metrics
            ) VALUES (
                :sid, :name, :primary_wallet_name, :wallet_names, :status,
                :goal, :tags, :notes, :created_at, :updated_at, :closed_at,
                :metrics, :wallet_metrics
            )
            """,
            row,
        )
        self._dl.db.commit()
        return self.get_session(session.sid) or session

    def delete_session(self, sid: str) -> bool:
        """
        Delete a session by sid.

        Returns True if a row was deleted, False otherwise.
        """

        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return False
        cursor.execute("DELETE FROM sessions WHERE sid = ?", (sid,))
        self._dl.db.commit()
        return bool(cursor.rowcount)
