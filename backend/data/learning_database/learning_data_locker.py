"""LearningDataLocker – isolated SQLite DB for telemetry."""
import os
from typing import Optional
from backend.core.core_imports import log
from backend.data.database import DatabaseManager
from backend.data.data_locker import DataLocker

DEFAULT_PATH = os.getenv("LEARNING_DB_PATH") or os.path.expanduser("~/.app/learning.db")

class LearningDataLocker(DataLocker):
    """Lightweight DataLocker for the learning database."""

    _instance: Optional["LearningDataLocker"] = None

    def __init__(self, db_path: str = DEFAULT_PATH):
        # Intentionally avoid heavy DataLocker init
        self.db = DatabaseManager(db_path)
        try:
            self.initialize_database()
        except Exception as e:  # pragma: no cover - init rarely fails
            log.error(f"❌ LearningDataLocker init failed: {e}", source="LearningDataLocker")
        else:
            log.debug("learning.db ready", source="LearningDataLocker")

    # Singleton accessor
    @classmethod
    def get_instance(cls) -> "LearningDataLocker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # Override DataLocker init callback
    def initialize_database(self):
        ddl = [
            """
            CREATE TABLE IF NOT EXISTS position_events (
                event_id TEXT PRIMARY KEY,
                position_id TEXT,
                trader_name TEXT,
                ts TEXT,
                state TEXT,
                travel_percent REAL,
                liquidation_distance REAL,
                heat_index REAL,
                value REAL,
                leverage REAL,
                pnl_after_fees REAL,
                is_hedged INTEGER,
                alert_level TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS hedge_events (
                event_id TEXT PRIMARY KEY,
                hedge_id TEXT,
                trader_name TEXT,
                ts TEXT,
                total_long_sz REAL,
                total_short_sz REAL,
                hedge_ratio REAL,
                delta REAL,
                total_heat_index REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS price_ticks (
                tick_id TEXT PRIMARY KEY,
                asset_type TEXT,
                ts TEXT,
                price REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS alert_events (
                event_id TEXT PRIMARY KEY,
                alert_id TEXT,
                trader_name TEXT,
                ts TEXT,
                alert_type TEXT,
                level TEXT,
                evaluated_value REAL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS trader_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                trader_name TEXT,
                ts TEXT,
                wallet_balance REAL,
                portfolio_value REAL,
                heat_index REAL,
                mood TEXT,
                strategy_json TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS transaction_events (
                event_id           TEXT PRIMARY KEY,
                order_id           TEXT,
                position_id        TEXT,
                trader_name        TEXT,
                ts                 TEXT,
                asset_type         TEXT,
                side               TEXT,
                size               REAL,
                price              REAL,
                fees               REAL,
                pnl_estimated      REAL,
                classification     TEXT,
                pre_value          REAL,
                post_value         REAL,
                delta_value        REAL,
                notes              TEXT
            )
            """,
        ]
        cursor = self.db.get_cursor()
        for stmt in ddl:
            cursor.execute(stmt)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_transaction_ts ON transaction_events(ts)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_tx_trader_ts "
            "ON transaction_events (trader_name, ts DESC)"
        )
        self.db.commit()
        log.success("✅ learning.db schema ready", source="LearningDataLocker")
