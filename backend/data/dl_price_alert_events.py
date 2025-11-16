from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from backend.core.logging import log
from backend.models.price_alert_event import PriceAlertEvent


class DLPriceAlertEventsManager:
    TABLE_NAME = "price_alert_events"

    def __init__(self, db) -> None:
        self.db = db
        log.debug("DLPriceAlertEventsManager initialized", source="DLPriceAlertEventsManager")

    # ---------------------------------------------------------------- schema --

    @staticmethod
    def initialize_schema(db) -> None:
        cursor = db.get_cursor()
        if cursor is None:
            log.error("DB unavailable creating price_alert_events", source="DLPriceAlertEventsManager")
            return

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {DLPriceAlertEventsManager.TABLE_NAME} (
                id TEXT PRIMARY KEY,
                alert_id INTEGER,
                asset TEXT,
                event_type TEXT,
                state_after TEXT,
                price_at_event REAL,
                anchor_at_event REAL,
                movement_value REAL,
                movement_percent REAL,
                threshold_value REAL,
                rule_type TEXT,
                direction TEXT,
                recurrence_mode TEXT,
                source TEXT,
                note TEXT,
                channels_result TEXT,
                created_at TEXT
            )
            """
        )
        db.commit()

        cursor.execute(
            f"PRAGMA table_info({DLPriceAlertEventsManager.TABLE_NAME})"
        )
        existing_cols = {row[1] for row in cursor.fetchall()}

        if "asset" not in existing_cols:
            cursor.execute(
                f"ALTER TABLE {DLPriceAlertEventsManager.TABLE_NAME} ADD COLUMN asset TEXT"
            )
            db.commit()

    @staticmethod
    def ensure_schema(db) -> None:
        try:
            DLPriceAlertEventsManager.initialize_schema(db)
        except Exception as e:
            log.warning(
                f"price_alert_events.initialize_schema failed: {e}",
                source="DLPriceAlertEventsManager",
            )

    # ------------------------------------------------------------ public API --

    def record_event(self, event: PriceAlertEvent) -> None:
        data = event.to_dict()
        if not data.get("id"):
            data["id"] = str(uuid4())
        if not data.get("created_at"):
            data["created_at"] = datetime.utcnow().isoformat()

        ch = data.get("channels_result")
        if ch is not None and not isinstance(ch, str):
            try:
                data["channels_result"] = json.dumps(ch)
            except Exception:
                data["channels_result"] = json.dumps({"_raw": str(ch)})

        cursor = self.db.get_cursor()
        if cursor is None:
            return

        cols = list(data.keys())
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO {self.TABLE_NAME} ({', '.join(cols)}) VALUES ({placeholders})"
        cursor.execute(sql, [data[c] for c in cols])
        self.db.commit()

    def get_recent(
        self,
        limit: int = 50,
        asset: Optional[str] = None,
        alert_id: Optional[int] = None,
    ) -> List[PriceAlertEvent]:
        cursor = self.db.get_cursor()
        if cursor is None:
            return []

        clauses = []
        params: list = []

        if asset:
            clauses.append("asset = ?")
            params.append(asset)
        if alert_id is not None:
            clauses.append("alert_id = ?")
            params.append(alert_id)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            f"SELECT * FROM {self.TABLE_NAME} "
            f"{where} ORDER BY created_at DESC LIMIT ?"
        )
        params.append(limit)
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        out: List[PriceAlertEvent] = []
        for row in rows:
            data = dict(row)
            ch_raw = data.get("channels_result")
            if isinstance(ch_raw, str) and ch_raw:
                try:
                    data["channels_result"] = json.loads(ch_raw)
                except Exception:
                    pass
            out.append(PriceAlertEvent(**data))
        return out
