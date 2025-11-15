"""
DLPriceAlertEventsManager

Handles the append-only ``price_alert_events`` table used by Market Core
and the Market Console "Event History" screen.
"""

from __future__ import annotations

from uuid import uuid4
from datetime import datetime
from typing import List, Optional, Union

import sqlite3

from backend.core.logging import log
from backend.models.price_alert_event import PriceAlertEvent


class DLPriceAlertEventsManager:
    TABLE_NAME = "price_alert_events"

    def __init__(self, db):
        self.db = db
        log.debug(
            "DLPriceAlertEventsManager initialized.",
            source="DLPriceAlertEventsManager",
        )

    # ------------------------------------------------------------------ schema

    @staticmethod
    def initialize_schema(db) -> None:
        """Create the ``price_alert_events`` table if it doesn't exist."""
        cursor = db.get_cursor()
        if cursor is None:
            log.error(
                "DB unavailable during price_alert_events.initialize_schema",
                source="DLPriceAlertEventsManager",
            )
            return

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {DLPriceAlertEventsManager.TABLE_NAME} (
                id TEXT PRIMARY KEY,
                alert_id TEXT,
                symbol TEXT,
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

    @staticmethod
    def ensure_schema(db) -> None:
        """
        Idempotent guard to ensure the table exists. Safe to run at startup.

        We keep this separate from DataLocker.initialize_database() so tests and
        standalone tools can bootstrap a DB without the whole DataLocker stack.
        """
        try:
            DLPriceAlertEventsManager.initialize_schema(db)
        except Exception as e:
            log.warning(
                f"price_alert_events.initialize_schema failed (continuing): {e}",
                source="DLPriceAlertEventsManager",
            )

    # ----------------------------------------------------------------- helpers

    def _sanitize_payload(self, payload: dict) -> dict:
        """
        Strip unknown keys based on the actual table schema.

        This keeps the DB insert resilient if the model grows extra fields.
        """
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                return payload
            cursor.execute(f"PRAGMA table_info({self.TABLE_NAME});")
            cols = {row[1] for row in cursor.fetchall()}
            sanitized = {k: v for k, v in payload.items() if k in cols}
            missing = set(payload.keys()) - cols
            if missing:
                log.debug(
                    f"price_alert_events: stripped non-schema keys: {missing}",
                    source="DLPriceAlertEventsManager",
                )
            return sanitized
        except sqlite3.DatabaseError as e:
            log.error(
                f"Failed to inspect table_info({self.TABLE_NAME}): {e}",
                source="DLPriceAlertEventsManager",
            )
            return payload

    # -------------------------------------------------------------- CRUD-ish --

    def record_event(
        self,
        event: Union[PriceAlertEvent, dict],
        *,
        ensure_schema_first: bool = False,
    ) -> None:
        """
        Insert a new event row.

        ``event`` can be a PriceAlertEvent or a plain dict. Missing fields like
        ``id`` and ``created_at`` will be filled automatically.
        """
        from json import dumps
        import traceback

        if ensure_schema_first:
            self.ensure_schema(self.db)

        try:
            if not isinstance(event, dict):
                event = (
                    event.model_dump()
                    if hasattr(event, "model_dump")
                    else event.dict()
                )

            event.setdefault("id", str(uuid4()))
            event.setdefault(
                "created_at", datetime.utcnow().isoformat()
            )

            # channels_result goes through JSON serialization
            channels = event.get("channels_result")
            if channels is not None and not isinstance(channels, str):
                try:
                    event["channels_result"] = dumps(channels)
                except Exception:
                    # best-effort serialization
                    event["channels_result"] = str(channels)

            sanitized = self._sanitize_payload(event)
            if not sanitized:
                log.warning(
                    "Attempted to record empty price_alert_event payload.",
                    source="DLPriceAlertEventsManager",
                )
                return

            fields = ", ".join(sanitized.keys())
            placeholders = ", ".join(f":{k}" for k in sanitized.keys())
            sql = (
                f"INSERT INTO {self.TABLE_NAME} ({fields}) "
                f"VALUES ({placeholders})"
            )

            cursor = self.db.get_cursor()
            if cursor is None:
                log.error(
                    "DB unavailable while recording price_alert_event",
                    source="DLPriceAlertEventsManager",
                )
                return

            cursor.execute(sql, sanitized)
            self.db.commit()
            log.debug(
                f"💾 PriceAlertEvent inserted: {sanitized.get('id')}",
                source="DLPriceAlertEventsManager",
            )
        except Exception as e:
            tb = traceback.format_exc()
            log.error(
                f"❌ Failed to record price_alert_event: {e}",
                source="DLPriceAlertEventsManager",
            )
            log.debug(tb, source="DLPriceAlertEventsManager")

    def get_recent(
        self,
        limit: int = 100,
        symbol: Optional[str] = None,
        alert_id: Optional[str] = None,
    ) -> List[PriceAlertEvent]:
        """
        Return the most recent events, optionally filtered by symbol or alert_id.
        """
        from json import loads

        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error(
                    "DB unavailable while fetching price_alert_events",
                    source="DLPriceAlertEventsManager",
                )
                return []

            clauses = []
            params: list = []

            if symbol:
                clauses.append("symbol = ?")
                params.append(symbol)
            if alert_id:
                clauses.append("alert_id = ?")
                params.append(alert_id)

            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            sql = (
                f"SELECT * FROM {self.TABLE_NAME} "
                f"{where} ORDER BY created_at DESC LIMIT ?"
            )
            params.append(limit)

            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

            out: List[PriceAlertEvent] = []
            for row in rows:
                data = dict(row)
                ch_raw = data.get("channels_result")
                if isinstance(ch_raw, str) and ch_raw:
                    try:
                        data["channels_result"] = loads(ch_raw)
                    except Exception:
                        # keep raw string on parse failure
                        pass
                out.append(PriceAlertEvent(**data))
            return out
        except Exception as e:
            log.error(
                f"❌ Failed to fetch price_alert_events: {e}",
                source="DLPriceAlertEventsManager",
            )
            return []

    def delete_all(self) -> None:
        """Dangerous helper for dev tools / tests."""
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error(
                    "DB unavailable, cannot wipe price_alert_events",
                    source="DLPriceAlertEventsManager",
                )
                return
            cursor.execute(f"DELETE FROM {self.TABLE_NAME}")
            self.db.commit()
            log.success(
                "🧹 All price_alert_events wiped",
                source="DLPriceAlertEventsManager",
            )
        except Exception as e:
            log.error(
                f"❌ Failed to wipe price_alert_events: {e}",
                source="DLPriceAlertEventsManager",
            )
