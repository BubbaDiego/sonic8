from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from backend.data.data_locker import DataLocker
from backend.core.session_core.session_models import Session, SessionStatus


class DLSessions:
    """
    DataLocker facade for the 'sessions' table.

    Minimal schema:

        CREATE TABLE IF NOT EXISTS sessions (
            sid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            primary_wallet_name TEXT NOT NULL,
            status TEXT NOT NULL,
            goal TEXT,
            tags TEXT NOT NULL,         -- JSON array of strings
            notes TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,   -- ISO-8601 UTC string
            updated_at TEXT NOT NULL,
            closed_at TEXT
        );

    Codex may adjust column names/types to match any pre-existing table.
    """

    def __init__(self, dl: DataLocker) -> None:
        self._dl = dl
        self._ensure_table()

    # ------------------------------------------------------------------ #
    # Schema bootstrap                                                   #
    # ------------------------------------------------------------------ #

    def _ensure_table(self) -> None:
        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return

        cursor.execute("PRAGMA table_info(sessions)")
        cols = {row[1] for row in cursor.fetchall() or []}
        base_expected = {
            "sid",
            "name",
            "primary_wallet_name",
            "status",
            "goal",
            "tags",
            "notes",
            "created_at",
            "updated_at",
            "closed_at",
        }

        if cols and not base_expected.issubset(cols):
            # Preserve any legacy table by renaming before creating the new schema.
            try:
                cursor.execute("ALTER TABLE sessions RENAME TO sessions_legacy")
            except Exception:
                pass

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                sid TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                primary_wallet_name TEXT NOT NULL,
                status TEXT NOT NULL,
                goal TEXT,
                tags TEXT NOT NULL,
                notes TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                closed_at TEXT
            )
            """
        )

        # Add enabled column for legacy installs that predate it.
        if cols and "enabled" not in cols:
            try:
                cursor.execute(
                    "ALTER TABLE sessions ADD COLUMN enabled INTEGER NOT NULL DEFAULT 1"
                )
            except Exception:
                pass

        self._dl.db.commit()

    # ------------------------------------------------------------------ #
    # Row ↔ model helpers                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _row_to_session(row: dict) -> Session:
        tags_raw = row.get("tags")
        if isinstance(tags_raw, str):
            try:
                tags = json.loads(tags_raw) or []
            except Exception:
                tags = []
        else:
            tags = []

        def _parse_ts(value: Optional[str]) -> Optional[datetime]:
            if not value:
                return None
            try:
                return datetime.fromisoformat(value)
            except Exception:
                return None

        return Session(
            sid=row["sid"],
            name=row["name"],
            primary_wallet_name=row["primary_wallet_name"],
            status=SessionStatus(row["status"]),
            goal=row.get("goal"),
            tags=tags,
            notes=row.get("notes") or "",
            enabled=bool(row.get("enabled", 1)),
            created_at=_parse_ts(row.get("created_at")) or datetime.utcnow(),
            updated_at=_parse_ts(row.get("updated_at")) or datetime.utcnow(),
            closed_at=_parse_ts(row.get("closed_at")),
        )

    @staticmethod
    def _session_to_row(session: Session) -> dict:
        return {
            "sid": session.sid,
            "name": session.name,
            "primary_wallet_name": session.primary_wallet_name,
            "status": session.status.value,
            "goal": session.goal,
            "tags": json.dumps(session.tags),
            "notes": session.notes,
            "enabled": 1 if session.enabled else 0,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "closed_at": session.closed_at.isoformat() if session.closed_at else None,
        }

    # ------------------------------------------------------------------ #
    # CRUD API                                                           #
    # ------------------------------------------------------------------ #

    def list_sessions(self, active_only: bool = False, enabled_only: bool = False) -> List[Session]:
        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return []

        where = []
        params: List[str] = []

        if active_only:
            where.append("status = ?")
            params.append(SessionStatus.ACTIVE.value)

        if enabled_only:
            where.append("enabled = 1")

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        cursor.execute(
            f"SELECT sid, name, primary_wallet_name, status, goal, tags, notes, enabled, "
            f"created_at, updated_at, closed_at FROM sessions {where_sql} "
            f"ORDER BY status = 'active' DESC, created_at DESC",
            params,
        )
        rows = [dict(row) for row in cursor.fetchall() or []]
        return [self._row_to_session(r) for r in rows]

    def get_session(self, sid: str) -> Optional[Session]:
        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return None

        cursor.execute(
            "SELECT sid, name, primary_wallet_name, status, goal, tags, notes, enabled, "
            "created_at, updated_at, closed_at FROM sessions WHERE sid = ?",
            (sid,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_session(dict(row))

    def get_session_by_sid(self, sid: str) -> Optional[Session]:
        return self.get_session(sid)

    def upsert_session(self, session: Session) -> Session:
        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return session

        row = self._session_to_row(session)
        cursor.execute(
            """
            INSERT INTO sessions (
                sid, name, primary_wallet_name, status, goal, tags, notes,
                enabled, created_at, updated_at, closed_at
            )
            VALUES (
                :sid, :name, :primary_wallet_name, :status, :goal, :tags, :notes,
                :enabled, :created_at, :updated_at, :closed_at
            )
            ON CONFLICT(sid) DO UPDATE SET
                name = excluded.name,
                primary_wallet_name = excluded.primary_wallet_name,
                status = excluded.status,
                goal = excluded.goal,
                tags = excluded.tags,
                notes = excluded.notes,
                enabled = excluded.enabled,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                closed_at = excluded.closed_at
            """,
            row,
        )
        self._dl.db.commit()
        return session

    def set_enabled(self, sid: str, enabled: bool) -> Optional[Session]:
        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return None

        now = datetime.utcnow().isoformat()
        cursor.execute(
            "UPDATE sessions SET enabled = ?, updated_at = ? WHERE sid = ?",
            (1 if enabled else 0, now, sid),
        )
        self._dl.db.commit()
        if cursor.rowcount <= 0:
            return None
        return self.get_session_by_sid(sid)

    def delete_session(self, sid: str) -> bool:
        cursor = self._dl.db.get_cursor() if getattr(self._dl, "db", None) else None
        if cursor is None:
            return False

        cursor.execute("DELETE FROM sessions WHERE sid = ?", (sid,))
        self._dl.db.commit()
        return bool(cursor.rowcount)
