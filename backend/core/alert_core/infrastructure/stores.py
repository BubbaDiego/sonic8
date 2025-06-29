from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import List

from backend.models.alert import Alert, AlertLog, AlertLevel


class _DBAdapter:
    """Lightweight SQLite adapter with a connect() context manager."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or ":memory:"
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row

    @contextmanager
    def connect(self):
        conn = self._conn
        try:
            yield conn
        finally:
            conn.commit()


def _ensure_alerts(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            description TEXT,
            alert_class TEXT,
            alert_type TEXT,
            trigger_value REAL,
            evaluated_value REAL,
            condition TEXT,
            level TEXT,
            notification_type TEXT,
            created_at TEXT,
            position_reference_id TEXT
        )
        """
    )


def _ensure_log(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_log (
            id TEXT PRIMARY KEY,
            alert_id TEXT,
            phase TEXT,
            level TEXT,
            message TEXT,
            payload TEXT,
            timestamp TEXT
        )
        """
    )


class AlertStore:
    def __init__(self, db: _DBAdapter | None = None) -> None:
        self.db = db or _DBAdapter()
        with self.db.connect() as conn:
            _ensure_alerts(conn)

    def create(self, alert: Alert) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO alerts (
                    id, description, alert_class, alert_type, trigger_value,
                    evaluated_value, condition, level, notification_type,
                    created_at, position_reference_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.id,
                    alert.description,
                    alert.alert_class,
                    alert.alert_type,
                    alert.trigger_value,
                    alert.evaluated_value,
                    alert.condition.value,
                    alert.level.value,
                    alert.notification_type.value,
                    alert.created_at.isoformat(),
                    alert.position_reference_id,
                ),
            )

    def list_active(self) -> List[Alert]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM alerts").fetchall()
        alerts = []
        for r in rows:
            alerts.append(
                Alert(
                    id=r["id"],
                    description=r["description"],
                    alert_class=r["alert_class"],
                    alert_type=r["alert_type"],
                    trigger_value=r["trigger_value"],
                    evaluated_value=r["evaluated_value"],
                    condition=r["condition"],
                    level=AlertLevel(r["level"]),
                    notification_type=r["notification_type"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                    position_reference_id=r["position_reference_id"],
                )
            )
        return alerts

    def update_level_value(self, id: str, level: str, value: float) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE alerts SET level = ?, evaluated_value = ? WHERE id = ?",
                (level, value, id),
            )


class AlertLogStore:
    def __init__(self, db: _DBAdapter | None = None) -> None:
        self.db = db or _DBAdapter()
        with self.db.connect() as conn:
            _ensure_log(conn)

    def append(self, entry: AlertLog) -> None:
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO alert_log (
                    id, alert_id, phase, level, message, payload, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.alert_id,
                    entry.phase,
                    entry.level,
                    entry.message,
                    json.dumps(entry.payload) if entry.payload is not None else None,
                    entry.timestamp.isoformat(),
                ),
            )

    def list(self, alert_id: str | None = None) -> List[AlertLog]:
        with self.db.connect() as conn:
            if alert_id:
                rows = conn.execute(
                    "SELECT * FROM alert_log WHERE alert_id = ?", (alert_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM alert_log").fetchall()
        logs = []
        for r in rows:
            payload = r["payload"]
            logs.append(
                AlertLog(
                    id=r["id"],
                    alert_id=r["alert_id"],
                    phase=r["phase"],
                    level=r["level"],
                    message=r["message"],
                    payload=json.loads(payload) if payload else None,
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                )
            )
        return logs
