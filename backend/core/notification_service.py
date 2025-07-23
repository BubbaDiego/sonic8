"""NotificationService – lightweight CRUD for in-app alert list.

Every call is safe against missing schema; the table is created on demand.
Purges entries older than 30 days on each insert.
"""
from datetime import datetime, timedelta, timezone
import uuid

class NotificationService:
    TABLE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        created_at TEXT,
        level TEXT,
        subject TEXT,
        body TEXT,
        initiator TEXT,
        comm_type TEXT,
        read INTEGER DEFAULT 0
    )
    """

    def __init__(self, db):
        self.db = db
        self._ensure_schema()

    # --------------------------------------------------------------
    # internal
    # --------------------------------------------------------------
    def _ensure_schema(self):
        cur = self.db.get_cursor()
        cur.execute(self.TABLE_SCHEMA)
        self.db.commit()

    def _purge_old(self, days: int = 30):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cur = self.db.get_cursor()
        cur.execute("DELETE FROM notifications WHERE created_at < ?", (cutoff,))
        self.db.commit()

    # --------------------------------------------------------------
    # public
    # --------------------------------------------------------------
    def insert(self, *, level: str, subject: str, body: str, initiator: str, comm_type: str = ""):
        self._purge_old()
        cur = self.db.get_cursor()
        entry = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "subject": subject[:120],
            "body": body,
            "initiator": initiator,
            "comm_type": comm_type,
            "read": 0
        }
        cur.execute("""INSERT INTO notifications
            (id, created_at, level, subject, body, initiator, comm_type, read)
            VALUES (:id, :created_at, :level, :subject, :body, :initiator, :comm_type, :read)
        """, entry)
        self.db.commit()
        return entry["id"]

    def list(self, status: str = "all", limit: int = 30):
        sql = "SELECT * FROM notifications"
        params = ()
        if status == "unread":
            sql += " WHERE read = 0"
        elif status == "new":
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            sql += " WHERE created_at >= ?"
            params = (cutoff,)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params += (limit,)
        cur = self.db.get_cursor()
        rows = cur.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def mark_read(self, notif_id: str):
        cur = self.db.get_cursor()
        cur.execute("UPDATE notifications SET read = 1 WHERE id = ?", (notif_id,))
        self.db.commit()

    def mark_all_read(self):
        cur = self.db.get_cursor()
        cur.execute("UPDATE notifications SET read = 1 WHERE read = 0")
        self.db.commit()

    def unread_count(self) -> int:
        cur = self.db.get_cursor()
        return cur.execute("SELECT COUNT(*) FROM notifications WHERE read = 0").fetchone()[0]
