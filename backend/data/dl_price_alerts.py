from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from backend.core.logging import log
from backend.models.price_alert import PriceAlert


class DLPriceAlertManager:
    TABLE_NAME = "price_alerts"

    def __init__(self, db) -> None:
        self.db = db
        log.debug("DLPriceAlertManager initialized", source="DLPriceAlertManager")

    # ---------------------------------------------------------------- schema --

    @staticmethod
    def initialize_schema(db) -> None:
        cursor = db.get_cursor()
        if cursor is None:
            log.error(
                "DB unavailable creating price_alerts",
                source="DLPriceAlertManager",
            )
            return

        # Base table definition – includes the latest set of columns
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {DLPriceAlertManager.TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                label TEXT,
                rule_type TEXT NOT NULL,
                direction TEXT NOT NULL,
                base_threshold_value REAL NOT NULL,
                recurrence_mode TEXT NOT NULL,
                cooldown_seconds INTEGER NOT NULL DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 1,

                original_anchor_price REAL,
                original_anchor_time TEXT,
                current_anchor_price REAL,
                current_anchor_time TEXT,
                effective_threshold_value REAL,
                armed INTEGER NOT NULL DEFAULT 1,

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

        # --- Backfill any missing columns (migration-friendly) ---
        cursor.execute(f"PRAGMA table_info({DLPriceAlertManager.TABLE_NAME})")
        existing = {row[1] for row in cursor.fetchall()}

        # name, sql-type, default SQL literal (or None)
        expected_cols = [
            ("label", "TEXT", None),
            ("effective_threshold_value", "REAL", None),
            ("last_distance_to_target", "REAL", None),
            ("last_proximity_ratio", "REAL", None),
            ("last_reset_at", "TEXT", None),
        ]

        for name, sql_type, default in expected_cols:
            if name not in existing:
                if default is None:
                    alter_sql = (
                        f"ALTER TABLE {DLPriceAlertManager.TABLE_NAME} "
                        f"ADD COLUMN {name} {sql_type}"
                    )
                else:
                    alter_sql = (
                        f"ALTER TABLE {DLPriceAlertManager.TABLE_NAME} "
                        f"ADD COLUMN {name} {sql_type} DEFAULT {default}"
                    )
                cursor.execute(alter_sql)

        db.commit()

    @staticmethod
    def ensure_schema(db) -> None:
        try:
            DLPriceAlertManager.initialize_schema(db)
        except Exception as e:
            log.warning(
                f"price_alerts.initialize_schema failed: {e}",
                source="DLPriceAlertManager",
            )

    # --------------------------------------------------------------- helpers --

    def _row_to_model(self, row) -> PriceAlert:
        data = dict(row)
        meta_raw = data.get("metadata")
        if isinstance(meta_raw, str) and meta_raw:
            try:
                data["metadata"] = json.loads(meta_raw)
            except Exception:
                pass
        return PriceAlert(**data)

    def _model_to_row(self, alert: PriceAlert) -> dict:
        data = alert.to_dict()
        meta = data.get("metadata")
        if meta is not None and not isinstance(meta, str):
            try:
                data["metadata"] = json.dumps(meta)
            except Exception:
                data["metadata"] = json.dumps({"_raw": str(meta)})
        return data

    # ------------------------------------------------------------ public API --

    def list_alerts(self, asset: Optional[str] = None) -> List[PriceAlert]:
        cursor = self.db.get_cursor()
        if cursor is None:
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

    def get_alert(self, alert_id: int) -> Optional[PriceAlert]:
        cursor = self.db.get_cursor()
        if cursor is None:
            return None
        cursor.execute(
            f"SELECT * FROM {self.TABLE_NAME} WHERE id = ?",
            (alert_id,),
        )
        row = cursor.fetchone()
        return self._row_to_model(row) if row else None

    def save_alert(self, alert: PriceAlert) -> PriceAlert:
        now = datetime.utcnow().isoformat()
        if not alert.created_at:
            alert.created_at = now
        alert.updated_at = now

        data = self._model_to_row(alert)
        cursor = self.db.get_cursor()
        if cursor is None:
            return alert

        if alert.id is None:
            cols = [k for k in data.keys() if k != "id"]
            placeholders = ", ".join("?" for _ in cols)
            sql = f"INSERT INTO {self.TABLE_NAME} ({', '.join(cols)}) VALUES ({placeholders})"
            cursor.execute(sql, [data[c] for c in cols])
            self.db.commit()
            alert.id = cursor.lastrowid
            log.debug(f"Inserted price_alert id={alert.id}", source="DLPriceAlertManager")
        else:
            cols = [k for k in data.keys() if k != "id"]
            assignments = ", ".join(f"{c} = ?" for c in cols)
            sql = f"UPDATE {self.TABLE_NAME} SET {assignments} WHERE id = ?"
            cursor.execute(sql, [data[c] for c in cols] + [alert.id])
            self.db.commit()
            log.debug(f"Updated price_alert id={alert.id}", source="DLPriceAlertManager")

        return alert

    def delete_alert(self, alert_id: int) -> None:
        cursor = self.db.get_cursor()
        if cursor is None:
            return
        cursor.execute(
            f"DELETE FROM {self.TABLE_NAME} WHERE id = ?",
            (alert_id,),
        )
        self.db.commit()
        log.debug(f"Deleted price_alert id={alert_id}", source="DLPriceAlertManager")
