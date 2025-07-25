from __future__ import annotations
import json
from typing import Any

from backend.core.logging import log


class DLNotificationManager:
    """Helper class persisting monitor events to *sonic_monitor_log*."""

    def __init__(self, db) -> None:
        """Create manager with a :class:`DatabaseManager` or sqlite connection."""
        self._db = db

    # ------------------------------------------------------------------ #
    # Writes
    # ------------------------------------------------------------------ #
    def insert(
        self,
        monitor: str,
        level: str,
        subject: str,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        cur = self._get_cursor()
        if not cur:
            return
        cur.execute(
            """INSERT INTO sonic_monitor_log
                    (monitor_name, level, subject, body, metadata)
                 VALUES (?, ?, ?, ?, json(?))""",
            (monitor, level, subject, body, json.dumps(metadata or {})),
        )
        self._commit()

    # ------------------------------------------------------------------ #
    # Reads
    # ------------------------------------------------------------------ #
    def list(self, status: str = "all", limit: int = 50) -> list[dict]:
        q = "SELECT * FROM sonic_monitor_log "
        if status in ("unread", "new"):
            q += "WHERE read = 0 "
        q += "ORDER BY created_at DESC LIMIT ?"
        cur = self._get_cursor()
        if not cur:
            return []
        cur.execute(q, (limit,))
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def unread_count(self) -> int:
        cur = self._get_cursor()
        if not cur:
            return 0
        cur.execute("SELECT COUNT(*) FROM sonic_monitor_log WHERE read = 0")
        return cur.fetchone()[0]

    def mark_all_read(self) -> None:
        cur = self._get_cursor()
        if not cur:
            return
        cur.execute("UPDATE sonic_monitor_log SET read = 1 WHERE read = 0")
        self._commit()

    def mark_read(self, notif_id: str) -> None:
        cur = self._get_cursor()
        if not cur:
            return
        cur.execute(
            "UPDATE sonic_monitor_log SET read = 1 WHERE id = ?",
            (notif_id,),
        )
        self._commit()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _get_cursor(self):
        try:
            if hasattr(self._db, "get_cursor"):
                return self._db.get_cursor()
            return self._db.cursor()
        except Exception as exc:  # pragma: no cover - catastrophic failure
            log.error(f"Failed to obtain DB cursor: {exc}", source="DLNotificationMgr")
            return None

    def _commit(self) -> None:
        try:
            if hasattr(self._db, "commit"):
                self._db.commit()
            else:
                self._db.commit()
        except Exception as exc:
            log.error(f"Notification DB commit failed: {exc}", source="DLNotificationMgr")
