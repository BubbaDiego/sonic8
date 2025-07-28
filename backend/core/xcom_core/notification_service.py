"""New NotificationService backed by sonic_monitor_log."""

from typing import List, Dict
import sqlite3

from backend.data.dl_notification_manager import DLNotificationManager


class NotificationService:
    """Drop-in replacement for legacy service using sonic_monitor_log."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self._mgr = DLNotificationManager(db)

    # -------- public API -------------------------------------------------- #
    def list(self, status: str = "all", limit: int = 50) -> List[Dict]:
        return self._mgr.list(status=status, limit=limit)

    def unread_count(self) -> int:
        return self._mgr.unread_count()

    def mark_read(self, notif_id: str) -> None:
        self._mgr.mark_read(notif_id)

    def mark_all_read(self) -> None:
        self._mgr.mark_all_read()
