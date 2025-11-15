# -*- coding: utf-8 -*-
"""
DLPriceAlertManager

Persistent storage for price alerts used by Market Core and the Market Console.
Alerts are stored in a flat table; config + state come from backend.models.price_alert.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import sqlite3

from backend.core.logging import log
from backend.models.price_alert import (
    PriceAlert,
    PriceAlertConfig,
    PriceAlertState,
    PriceAlertMode,
    PriceAlertDirection,
    PriceAlertRecurrence,
    PriceAlertStateEnum,
)


class DLPriceAlertManager:
    TABLE_NAME = "price_alerts"

    def __init__(self, db) -> None:
        self.db = db
        log.debug(
            "DLPriceAlertManager initialized.",
            source="DLPriceAlertManager",
        )

    # ------------------------------------------------------------------ schema

    @staticmethod
    def initialize_schema(db) -> None:
        """
        Create the price_alerts table if it doesn't exist.

        We deliberately flatten config + state into columns instead of a single
        JSON blob to keep basic querying and debugging easy.
        """
        cursor = db.get_cursor()
        if cursor is None:
            log.error(
                "DB unavailable during price_alerts.initialize_schema",
                source="DLPriceAlertManager",
            )
            return

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {DLPriceAlertManager.TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                name TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,

                mode TEXT NOT NULL,
                direction TEXT NOT NULL,
                threshold_value REAL NOT NULL,
                original_threshold_value REAL,

                recurrence TEXT NOT NULL,
                cooldown_seconds INTEGER NOT NULL DEFAULT 0,

                original_anchor_price REAL,
                original_anchor_time TEXT,
                current_anchor_price REAL,
                current_anchor_time TEXT,

                armed INTEGER NOT NULL DEFAULT 1,
                fired_count INTEGER NOT NULL DEFAULT 0,

                last_state TEXT,
                last_price REAL,
                last_move_abs REAL,
                last_move_pct REAL,
                last_distance_to_target REAL,
                last_proximity_ratio REAL,
                last_evaluated_at TEXT,
                last_triggered_at TEXT,
                last_reset_at TEXT,

                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.commit()

    @staticmethod
    def ensure_schema(db) -> None:
        try:
            DLPriceAlertManager.initialize_schema(db)
        except Exception as e:
            log.warning(
                f"price_alerts.initialize_schema failed (continuing): {e}",
                source="DLPriceAlertManager",
            )

    # ----------------------------------------------------------------- helpers

    def _row_to_model(self, row: sqlite3.Row) -> PriceAlert:
        """Convert DB row → PriceAlert model."""
        r = dict(row)
        # Config
        cfg = PriceAlertConfig(
            id=r["id"],
            asset=r["asset"],
            name=r["name"],
            enabled=bool(r["enabled"]),
            mode=PriceAlertMode(r["mode"]),
            direction=PriceAlertDirection(r["direction"]),
            threshold_value=r["threshold_value"],
            original_threshold_value=r["original_threshold_value"],
            recurrence=PriceAlertRecurrence(r["recurrence"]),
            cooldown_seconds=r["cooldown_seconds"],
            metadata=json.loads(r["metadata"]) if r["metadata"] else {},
            created_at=datetime.fromisoformat(r["created_at"]),
            updated_at=datetime.fromisoformat(r["updated_at"]),
        )
        # State
        st = PriceAlertState(
            original_anchor_price=r["original_anchor_price"],
            original_anchor_time=(
                datetime.fromisoformat(r["original_anchor_time"])
                if r["original_anchor_time"]
                else None
            ),
            current_anchor_price=r["current_anchor_price"],
            current_anchor_time=(
                datetime.fromisoformat(r["current_anchor_time"])
                if r["current_anchor_time"]
                else None
            ),
            armed=bool(r["armed"]),
            fired_count=r["fired_count"],
            last_state=PriceAlertStateEnum(r["last_state"])
            if r["last_state"]
            else PriceAlertStateEnum.OK,
            last_price=r["last_price"],
            last_move_abs=r["last_move_abs"],
            last_move_pct=r["last_move_pct"],
            last_distance_to_target=r["last_distance_to_target"],
            last_proximity_ratio=r["last_proximity_ratio"],
            last_evaluated_at=(
                datetime.fromisoformat(r["last_evaluated_at"])
                if r["last_evaluated_at"]
                else None
            ),
            last_triggered_at=(
                datetime.fromisoformat(r["last_triggered_at"])
                if r["last_triggered_at"]
                else None
            ),
            last_reset_at=(
                datetime.fromisoformat(r["last_reset_at"])
                if r["last_reset_at"]
                else None
            ),
        )
        return PriceAlert(config=cfg, state=st)

    def _model_to_row_dict(self, alert: PriceAlert) -> Dict[str, Any]:
        """Flatten PriceAlert → dict suitable for parameterized SQL."""
        cfg = alert.config
        st = alert.state
        return {
            "id": cfg.id,
            "asset": cfg.asset,
            "name": cfg.name,
            "enabled": 1 if cfg.enabled else 0,
            "mode": cfg.mode.value,
            "direction": cfg.direction.value,
            "threshold_value": cfg.threshold_value,
            "original_threshold_value": cfg.original_threshold_value,
            "recurrence": cfg.recurrence.value,
            "cooldown_seconds": cfg.cooldown_seconds,
            "original_anchor_price": st.original_anchor_price,
            "original_anchor_time": st.original_anchor_time.isoformat()
            if st.original_anchor_time
            else None,
            "current_anchor_price": st.current_anchor_price,
            "current_anchor_time": st.current_anchor_time.isoformat()
            if st.current_anchor_time
            else None,
            "armed": 1 if st.armed else 0,
            "fired_count": st.fired_count,
            "last_state": st.last_state.value if st.last_state else None,
            "last_price": st.last_price,
            "last_move_abs": st.last_move_abs,
            "last_move_pct": st.last_move_pct,
            "last_distance_to_target": st.last_distance_to_target,
            "last_proximity_ratio": st.last_proximity_ratio,
            "last_evaluated_at": st.last_evaluated_at.isoformat()
            if st.last_evaluated_at
            else None,
            "last_triggered_at": st.last_triggered_at.isoformat()
            if st.last_triggered_at
            else None,
            "last_reset_at": st.last_reset_at.isoformat()
            if st.last_reset_at
            else None,
            "metadata": json.dumps(cfg.metadata or {}),
            "created_at": cfg.created_at.isoformat(),
            "updated_at": cfg.updated_at.isoformat(),
        }

    # -------------------------------------------------------------- CRUD-ish --

    def list_alerts(self, asset: Optional[str] = None) -> List[PriceAlert]:
        """Return all alerts, optionally filtered by asset symbol."""
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error(
                    "DB unavailable while fetching price_alerts",
                    source="DLPriceAlertManager",
                )
                return []
            if asset:
                cursor.execute(
                    f"SELECT * FROM {self.TABLE_NAME} WHERE asset = ? ORDER BY id ASC",
                    (asset,),
                )
            else:
                cursor.execute(
                    f"SELECT * FROM {self.TABLE_NAME} ORDER BY asset ASC, id ASC"
                )
            rows = cursor.fetchall()
            return [self._row_to_model(r) for r in rows]
        except Exception as e:
            log.error(
                f"Failed to list price_alerts: {e}",
                source="DLPriceAlertManager",
            )
            return []

    def get_alert(self, alert_id: int) -> Optional[PriceAlert]:
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                return None
            cursor.execute(
                f"SELECT * FROM {self.TABLE_NAME} WHERE id = ?",
                (alert_id,),
            )
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
        except Exception as e:
            log.error(
                f"Failed to get price_alert id={alert_id}: {e}",
                source="DLPriceAlertManager",
            )
            return None

    def save_alert(self, alert: PriceAlert) -> PriceAlert:
        """
        Insert or update an alert.

        If alert.config.id is None, perform an INSERT and update the id on return.
        """
        now = datetime.utcnow()
        cfg = alert.config.copy(update={"updated_at": now})
        if cfg.created_at is None:
            cfg.created_at = now
        st = alert.state

        row = self._model_to_row_dict(PriceAlert(config=cfg, state=st))

        cursor = self.db.get_cursor()
        if cursor is None:
            log.error("DB unavailable while saving price_alert", source="DLPriceAlertManager")
            return alert

        try:
            if cfg.id is None:
                # INSERT
                cols = [k for k in row.keys() if k != "id"]
                placeholders = ", ".join("?" for _ in cols)
                sql = (
                    f"INSERT INTO {self.TABLE_NAME} ({', '.join(cols)}) "
                    f"VALUES ({placeholders})"
                )
                cursor.execute(sql, [row[c] for c in cols])
                self.db.commit()
                new_id = cursor.lastrowid
                cfg.id = new_id
                log.debug(
                    f"Inserted price_alert id={new_id}",
                    source="DLPriceAlertManager",
                )
            else:
                # UPDATE
                cols = [k for k in row.keys() if k != "id"]
                assignments = ", ".join(f"{c} = ?" for c in cols)
                sql = (
                    f"UPDATE {self.TABLE_NAME} SET {assignments} "
                    f"WHERE id = ?"
                )
                cursor.execute(sql, [row[c] for c in cols] + [cfg.id])
                self.db.commit()
                log.debug(
                    f"Updated price_alert id={cfg.id}",
                    source="DLPriceAlertManager",
                )
        except Exception as e:
            log.error(
                f"Failed to save price_alert id={cfg.id}: {e}",
                source="DLPriceAlertManager",
            )

        return PriceAlert(config=cfg, state=st)

    def delete_alert(self, alert_id: int) -> None:
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                return
            cursor.execute(
                f"DELETE FROM {self.TABLE_NAME} WHERE id = ?",
                (alert_id,),
            )
            self.db.commit()
            log.debug(
                f"Deleted price_alert id={alert_id}",
                source="DLPriceAlertManager",
            )
        except Exception as e:
            log.error(
                f"Failed to delete price_alert id={alert_id}: {e}",
                source="DLPriceAlertManager",
            )
