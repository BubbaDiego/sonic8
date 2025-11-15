"""
DLPriceAlertEventsManager

Handles the append-only ``price_alert_events`` table used by Market Core
and the Market Console "Event History" screen.
"""

from __future__ import annotations

from uuid import uuid4
from datetime import datetime
from typing import List, Optional, Union, Dict, Any

import sqlite3
from enum import Enum

from backend.core.logging import log
from backend.models.price_alert import (
    PriceAlertDirection,
    PriceAlertMode,
    PriceAlertStateEnum,
)
from backend.models.price_alert_event import PriceAlertEvent, PriceAlertEventType


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
                alert_id INTEGER,
                asset TEXT,
                event_type TEXT,
                state_after TEXT,
                mode TEXT,
                direction TEXT,
                price REAL,
                anchor_price REAL,
                movement_abs REAL,
                movement_pct REAL,
                threshold_value REAL,
                distance_to_target REAL,
                proximity_ratio REAL,
                metadata TEXT,
                note TEXT,
                created_at TEXT NOT NULL
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

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime):
            return value.isoformat()
        return value

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
        ``id`` and ``created_at`` are auto-filled.
        """
        from json import dumps

        if ensure_schema_first:
            self.ensure_schema(self.db)

        try:
            if isinstance(event, PriceAlertEvent):
                payload: Dict[str, Any] = event.dict()
            elif hasattr(event, "dict"):
                payload = event.dict()
            else:
                payload = dict(event)

            payload.setdefault("id", str(uuid4()))
            payload.setdefault("created_at", datetime.utcnow())

            for key, value in list(payload.items()):
                payload[key] = self._normalize_value(value)

            metadata = payload.get("metadata")
            if metadata is not None and not isinstance(metadata, str):
                try:
                    payload["metadata"] = dumps(metadata)
                except Exception:
                    payload["metadata"] = str(metadata)

            sanitized = self._sanitize_payload(payload)
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
            import traceback

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
                clauses.append("asset = ?")
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
                data: Dict[str, Any] = dict(row)
                metadata_raw = data.get("metadata")
                if isinstance(metadata_raw, str) and metadata_raw:
                    try:
                        data["metadata"] = loads(metadata_raw)
                    except Exception:
                        pass

                created_at = data.get("created_at")
                if isinstance(created_at, str):
                    try:
                        data["created_at"] = datetime.fromisoformat(created_at)
                    except ValueError:
                        data["created_at"] = datetime.utcnow()

                for enum_field, enum_cls in (
                    ("state_after", PriceAlertStateEnum),
                    ("mode", PriceAlertMode),
                    ("direction", PriceAlertDirection),
                    ("event_type", PriceAlertEventType),
                ):
                    value = data.get(enum_field)
                    if value is not None and not isinstance(value, enum_cls):
                        try:
                            data[enum_field] = enum_cls(value)
                        except ValueError:
                            data[enum_field] = value

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
            log.warning("🧹 All price_alert_events wiped", source="DLPriceAlertEventsManager")
        except Exception as e:
            log.error(
                f"❌ Failed to wipe price_alert_events: {e}",
                source="DLPriceAlertEventsManager",
            )
