# data_locker.py
"""
Author: BubbaDiego
Module: DataLocker
Description:
    High-level orchestrator that composes all DL*Manager modules. This is the
    central access point for interacting with alerts, prices, positions, wallets,
    brokers, portfolio data, hedges, and global system state via a unified SQLite backend.

Dependencies:
    - DatabaseManager (SQLite wrapper)
    - DLAlertManager, DLPriceManager, etc.
"""

import os
import json
import sqlite3
from collections.abc import Mapping
from backend.data.database import DatabaseManager
from backend.data.dl_alerts import DLAlertManager
from backend.data.dl_prices import DLPriceManager
from backend.data.dl_positions import DLPositionManager
from backend.data.dl_wallets import DLWalletManager
from backend.data.dl_portfolio import DLPortfolioManager

try:  # pragma: no cover - optional dependency
    from backend.data.dl_system_data import DLSystemDataManager
except ModuleNotFoundError:
    DLSystemDataManager = None

from backend.data.dl_monitor_ledger import DLMonitorLedgerManager
from backend.data.dl_modifiers import DLModifierManager

try:  # pragma: no cover - optional dependency
    from backend.data.dl_hedges import DLHedgeManager
except ModuleNotFoundError:
    DLHedgeManager = None
try:  # pragma: no cover - optional dependency
    from backend.data.dl_traders import DLTraderManager
except ModuleNotFoundError:
    DLTraderManager = None

# Optional managers for thresholds
try:  # pragma: no cover - optional dependency
    from backend.data.dl_thresholds import DLThresholdManager
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    DLThresholdManager = None

try:  # pragma: no cover - optional dependency
    from backend.data.threshold_seeder import AlertThresholdSeeder
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    AlertThresholdSeeder = None

# Corrected explicitly absolute import
from backend.core.constants import (
    SONIC_SAUCE_PATH,
    BASE_DIR,
    MOTHER_DB_PATH,
    ALERT_THRESHOLDS_PATH,
    CONFIG_DIR,
)

from backend.core.core_imports import log  # Corrected clearly

try:
    from system.death_nail_service import DeathNailService
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    DeathNailService = None
from datetime import datetime


class DataLocker:
    """Singleton-style access point for all data managers."""

    _instance = None

    def __setattr__(self, name, value):
        if name == "db":
            if hasattr(self, "db"):
                current = object.__getattribute__(self, "db")
                if isinstance(current, DatabaseManager):
                    if not isinstance(value, DatabaseManager):
                        log.error(
                            f"Attempt to assign non-DatabaseManager to 'db': {type(value)}",
                            source="DataLocker",
                        )
                        raise TypeError("db must be a DatabaseManager instance")
                    if current is not value:
                        log.error(
                            "Attempt to reassign existing DatabaseManager instance",
                            source="DataLocker",
                        )
                        raise AttributeError(
                            "Cannot reassign 'db' once a DatabaseManager has been set"
                        )
            else:
                if not isinstance(value, DatabaseManager):
                    log.error(
                        f"Attempt to assign non-DatabaseManager to 'db': {type(value)}",
                        source="DataLocker",
                    )
                    raise TypeError("db must be a DatabaseManager instance")
        object.__setattr__(self, name, value)

    def __init__(self, db_path: str):
        self.db = DatabaseManager(db_path)
        if not isinstance(self.db, DatabaseManager):
            raise TypeError("db must be a DatabaseManager instance")

        self.alerts = DLAlertManager(self.db)
        self.prices = DLPriceManager(self.db)
        self.positions = DLPositionManager(self.db)
        self.hedges = DLHedgeManager(self.db) if DLHedgeManager else None
        self.wallets = DLWalletManager(self.db)
        self.portfolio = DLPortfolioManager(self.db)
        if DLTraderManager:
            try:
                self.traders = DLTraderManager(self.db)
            except Exception as e:
                log.error(
                    f"Failed to initialize DLTraderManager: {e}",
                    source="DataLocker",
                )
                self.traders = None
        else:
            self.traders = None
        self.system = DLSystemDataManager(self.db) if DLSystemDataManager else None
        self.ledger = DLMonitorLedgerManager(self.db)
        self.modifiers = DLModifierManager(self.db)

        try:
            self.initialize_database()
            self._seed_modifiers_if_empty()
            self._seed_wallets_if_empty()
            self._seed_alerts_if_empty()
            self._seed_thresholds_if_empty()
            self._ensure_travel_percent_threshold()
            if self.system is not None:
                self._seed_alert_config_if_empty()

        except Exception as e:
            log.error(f"❌ DataLocker setup failed: {e}", source="DataLocker")
        else:
            if self.db.conn:
                log.debug(
                    "All DL managers bootstrapped successfully.",
                    source="DataLocker",
                )
            else:
                log.warning(
                    "⚠️ DataLocker initialization failed: no DB connection",
                    source="DataLocker",
                )

    @classmethod
    def get_instance(cls, db_path: str = str(MOTHER_DB_PATH)):
        """Return a singleton instance of DataLocker."""
        if cls._instance is None or str(cls._instance.db.db_path) != str(db_path):
            cls._instance = cls(db_path)
        return cls._instance

    def initialize_database(self):
        """
        Creates all required tables in the database if they do not exist.
        This method can be run safely and repeatedly.
        """
        log.info("🔧 Initializing database schema...", source="DataLocker")
        cursor = self.db.get_cursor()
        if cursor is None:
            log.error("❌ Unable to obtain DB cursor during init", source="DataLocker")
            return

        table_defs = {
            "wallets": """
                CREATE TABLE IF NOT EXISTS wallets (
                    name TEXT PRIMARY KEY,
                    public_address TEXT,
                    chrome_profile TEXT DEFAULT 'Default',
                    private_address TEXT,
                    image_path TEXT,
                    balance REAL DEFAULT 0.0,
                    tags TEXT DEFAULT '',
                    is_active BOOLEAN DEFAULT 1,
                    type TEXT DEFAULT 'personal'
                )
            """,
            "alerts": """
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    created_at TEXT,
                    alert_type TEXT,
                    alert_class TEXT,
                    asset_type TEXT,
                    trigger_value REAL,
                    condition TEXT,
                    notification_type TEXT,
                    level TEXT,
                    last_triggered TEXT,
                    status TEXT,
                    frequency INTEGER,
                    counter INTEGER,
                    liquidation_distance REAL,
                    travel_percent REAL,
                    liquidation_price REAL,
                    notes TEXT,
                    description TEXT,
                    position_reference_id TEXT,
                    evaluated_value REAL,
                    position_type TEXT
                )
            """,
            "alert_thresholds": """
                CREATE TABLE IF NOT EXISTS alert_thresholds (
                    id TEXT PRIMARY KEY,
                    alert_type TEXT NOT NULL,
                    alert_class TEXT NOT NULL,
                    metric_key TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    low REAL NOT NULL,
                    medium REAL NOT NULL,
                    high REAL NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    last_modified TEXT DEFAULT CURRENT_TIMESTAMP,
                    low_notify TEXT,
                    medium_notify TEXT,
                    high_notify TEXT
                )
            """,
            "brokers": """
                CREATE TABLE IF NOT EXISTS brokers (
                    name TEXT PRIMARY KEY,
                    image_path TEXT,
                    web_address TEXT,
                    total_holding REAL DEFAULT 0.0
                )
            """,
            "positions": """
                CREATE TABLE IF NOT EXISTS positions (
                    id TEXT PRIMARY KEY,
                    asset_type TEXT,
                    position_type TEXT,
                    entry_price REAL,
                    liquidation_price REAL,
                    travel_percent REAL,
                    value REAL,
                    collateral REAL,
                    size REAL,
                    leverage REAL,
                    wallet_name TEXT,
                    last_updated TEXT,
                    alert_reference_id TEXT,
                    hedge_buddy_id TEXT,
                    current_price REAL,
                    liquidation_distance REAL,
                    heat_index REAL,
                    current_heat_index REAL,
                    pnl_after_fees_usd REAL,
                    status TEXT DEFAULT 'ACTIVE'
                )
            """,
            "positions_totals_history": """
                CREATE TABLE IF NOT EXISTS positions_totals_history (
                    id TEXT PRIMARY KEY,
                    snapshot_time TEXT,
                    total_size REAL,
                    total_long_size REAL,
                    total_short_size REAL,
                    total_value REAL,
                    total_collateral REAL,
                    avg_leverage REAL,
                    avg_travel_percent REAL,
                    avg_heat_index REAL,
                    total_heat_index REAL,
                    market_average_sp500 REAL,
                    session_start_time TEXT,
                    session_start_value REAL,
                    current_session_value REAL,
                    session_goal_value REAL,
                    session_performance_value REAL
                )
            """,
            "modifiers": """
            CREATE TABLE IF NOT EXISTS modifiers (
                key TEXT PRIMARY KEY,
                group_name TEXT NOT NULL,
                value REAL NOT NULL,
                last_modified TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            "prices": """
                CREATE TABLE IF NOT EXISTS prices (
                    id TEXT PRIMARY KEY,
                    asset_type TEXT,
                    current_price REAL,
                    previous_price REAL,
                    last_update_time TEXT,
                    previous_update_time TEXT,
                    source TEXT
                )
            """,
            "monitor_heartbeat": """
                CREATE TABLE IF NOT EXISTS monitor_heartbeat (
                    monitor_name TEXT PRIMARY KEY,
                    last_run TIMESTAMP NOT NULL,
                    interval_seconds INTEGER NOT NULL
                )
            """,
            "global_config": """
                CREATE TABLE IF NOT EXISTS global_config (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """,
            "system_vars": """
            CREATE TABLE IF NOT EXISTS system_vars (
    id TEXT PRIMARY KEY DEFAULT 'main',
    last_update_time_positions TEXT,
    last_update_positions_source TEXT,
    last_update_time_prices TEXT,
    last_update_prices_source TEXT,
    last_update_time_jupiter TEXT,
    last_update_jupiter_source TEXT,  -- ✅ ADD THIS
    theme_mode TEXT,
    theme_active_profile TEXT,        -- ✅ ADD THIS TOO
    strategy_start_value REAL,
    strategy_description TEXT
)
    
        """,
        }

        def _ensure_column(cursor, table, column_def):
            """Add a column to ``table`` if missing."""
            try:
                col_name = column_def.split()[0]
                existing = {
                    row[1] for row in cursor.execute(f"PRAGMA table_info({table})")
                }
                if col_name not in existing:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
                    log.info(
                        f"Added missing column {col_name} to {table}",
                        source="DataLocker",
                    )
            except Exception as e:
                log.error(
                    f"❌ Failed to ensure column {column_def} on {table}: {e}",
                    source="DataLocker",
                )

        for name, ddl in table_defs.items():
            log.debug(f"Ensuring table: {name}", source="DataLocker")
            try:
                cursor.execute(ddl)
                log.debug(f"Table ensured: {name}", source="DataLocker")
            except Exception as e:
                log.error(f"❌ Failed creating table {name}: {e}", source="DataLocker")

        # Ensure uniqueness for alert definition fields
        try:
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS alert_unique_idx
                    ON alerts(alert_type, alert_class, position_reference_id)
                """
            )
        except Exception as e:
            log.error(f"❌ Failed creating alert_unique_idx: {e}", source="DataLocker")

        log.info("✅ Table creation complete.", source="DataLocker")

        # --- Automatic schema migrations ---
        log.debug("Applying schema migrations", source="DataLocker")
        _ensure_column(cursor, "positions", "status TEXT DEFAULT 'ACTIVE'")
        _ensure_column(cursor, "wallets", "chrome_profile TEXT DEFAULT 'Default'")

        _ensure_column(cursor, "positions", "value REAL")
        _ensure_column(cursor, "positions", "collateral REAL")
        _ensure_column(cursor, "positions", "size REAL")
        _ensure_column(cursor, "positions", "leverage REAL")
        _ensure_column(cursor, "positions", "current_price REAL")
        _ensure_column(cursor, "positions", "pnl_after_fees_usd REAL")
        _ensure_column(cursor, "positions", "liquidation_distance REAL")
        _ensure_column(cursor, "positions", "stale INTEGER DEFAULT 0")
        _ensure_column(cursor, "positions", "hedge_buddy_id TEXT")
        _ensure_column(cursor, "positions_totals_history", "market_average_sp500 REAL")
        _ensure_column(cursor, "positions_totals_history", "total_long_size REAL")
        _ensure_column(cursor, "positions_totals_history", "total_short_size REAL")
        _ensure_column(cursor, "positions_totals_history", "total_heat_index REAL")
        _ensure_column(cursor, "positions_totals_history", "session_start_time TEXT")
        _ensure_column(cursor, "positions_totals_history", "session_start_value REAL")
        _ensure_column(cursor, "positions_totals_history", "current_session_value REAL")
        _ensure_column(cursor, "positions_totals_history", "session_goal_value REAL")
        _ensure_column(
            cursor, "positions_totals_history", "session_performance_value REAL"
        )

        # Ensure a default row exists for system vars so lookups don't fail
        log.debug("Ensuring system_vars default row", source="DataLocker")
        try:
            cursor.execute("INSERT OR IGNORE INTO system_vars (id) VALUES ('main')")
        except Exception as e:
            log.error(
                f"❌ Failed initializing system_vars default row: {e}",
                source="DataLocker",
            )

        try:
            self.db.commit()
            log.info("✅ Database initialization finished.", source="DataLocker")
        except sqlite3.DatabaseError as e:  # pragma: no cover - rare corruption case
            if "malformed" in str(e) or "file is not a database" in str(e):
                log.error(
                    f"❌ Database corruption detected: {e}. Recreating database.",
                    source="DataLocker",
                )
                try:
                    # DeathNailService(log).trigger({
                    #     "message": "Database initialization failure",
                    #     "payload": {"error": str(e)},
                    # })
                    log.info(
                        "🔈 Death nail suppressed during DB init failure",
                        source="DataLocker",
                    )
                except Exception as death_e:
                    log.error(
                        f"❌ Death nail trigger failed: {death_e}",
                        source="DataLocker",
                    )
                self.db.recover_database()
                # Retry initialization on a fresh DB
                self.initialize_database()
            else:
                log.error(f"❌ Commit failed during init: {e}", source="DataLocker")

    # Inside DataLocker class
    def read_positions(self):
        return self.positions.get_all_positions()

    def close(self):
        self.db.close()
        DataLocker._instance = None
        log.debug("DataLocker shutdown complete.", source="DataLocker")

    def get_latest_price(self, asset_type: str) -> dict:
        return self.prices.get_latest_price(asset_type)

    def set_last_update_times(self, updates: dict):
        if self.system is not None:
            self.system.set_last_update_times(updates)

    def get_last_update_times(self) -> dict:
        """Return last update times for positions and prices as a dict."""
        try:
            return (
                self.system.get_last_update_times().to_dict()
                if self.system is not None
                else {}
            )
        except Exception:
            return {}

    def get_death_log_entries(self, limit: int = 20) -> list:
        """Return the most recent entries from the death log file."""
        path = os.path.join(BASE_DIR, "death_log.txt")
        try:
            if not os.path.exists(path):
                return []
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            entries = [json.loads(l) for l in lines]
            return entries[-limit:]
        except Exception as e:
            log.error(f"❌ Failed to read death log: {e}", source="DataLocker")
            return []

    def get_system_alerts(self, limit: int = 20) -> list:
        """Return recent alerts belonging to the System class."""
        try:
            alerts = self.alerts.get_all_alerts()
            system_alerts = [a for a in alerts if a.get("alert_class") == "System"]
            return system_alerts[:limit]
        except Exception as e:
            log.error(f"❌ Failed to retrieve system alerts: {e}", source="DataLocker")
            return []

    def insert_or_update_price(self, asset_type, price, source="PriceMonitor"):
        from uuid import uuid4
        from datetime import datetime

        price_data = {
            "id": str(uuid4()),
            "asset_type": asset_type,
            "current_price": price,
            "previous_price": 0.0,
            "last_update_time": datetime.now().isoformat(),
            "previous_update_time": None,
            "source": source,
        }
        self.prices.insert_price(price_data)

    def get_position_by_reference_id(self, pos_id: str):
        return self.positions.get_position_by_id(pos_id)

    def get_wallet_by_name(self, wallet_name: str):
        return self.wallets.get_wallet_by_name(wallet_name)

    # Wallet convenience wrappers used by repositories
    def read_wallets(self):
        return self.wallets.get_wallets()

    def create_wallet(self, wallet: dict):
        self.wallets.create_wallet(wallet)

    def update_wallet(self, name: str, wallet: dict):
        self.wallets.update_wallet(name, wallet)

    def delete_positions_for_wallet(self, wallet_name: str):
        if hasattr(self.positions, "delete_positions_for_wallet"):
            self.positions.delete_positions_for_wallet(wallet_name)

    # ---- Portfolio convenience wrappers ----
    def get_portfolio_history(self):
        """Return all portfolio snapshot entries."""
        return self.portfolio.get_snapshots()

    def add_portfolio_entry(self, entry: dict):
        """Insert a snapshot entry into the portfolio history."""
        self.portfolio.add_entry(entry)

    def update_portfolio_entry(self, entry_id: str, fields: dict):
        """Update a portfolio history entry by its ID."""
        self.portfolio.update_entry(entry_id, fields)

    def get_portfolio_entry_by_id(self, entry_id: str):
        """Fetch a portfolio history entry by ID."""
        return self.portfolio.get_entry_by_id(entry_id)

    def delete_portfolio_entry(self, entry_id: str):
        """Delete a portfolio history entry."""
        self.portfolio.delete_entry(entry_id)

    def clear_portfolio_history(self):
        """Remove all records from the portfolio history table."""
        self.portfolio.clear_snapshots()

    def _seed_modifiers_if_empty(self):
        """Seed modifiers table from sonic_sauce.json if empty."""
        cursor = self.db.get_cursor()
        if not cursor:
            log.error("❌ DB unavailable, skipping modifier seed", source="DataLocker")
            return
        count = cursor.execute("SELECT COUNT(*) FROM modifiers").fetchone()[0]
        if count == 0:
            try:
                with open(SONIC_SAUCE_PATH, "r", encoding="utf-8") as f:
                    data = f.read()
                self.modifiers.import_from_json(data)
                log.debug("Modifiers seeded from sonic_sauce.json", source="DataLocker")
            except Exception as e:
                log.error(f"❌ Failed seeding modifiers: {e}", source="DataLocker")

    def _seed_wallets_if_empty(self):
        """Seed wallets table from wallets.json if empty."""
        cursor = self.db.get_cursor()
        if not cursor:
            log.error("❌ DB unavailable, skipping wallet seed", source="DataLocker")
            return
        count = cursor.execute("SELECT COUNT(*) FROM wallets").fetchone()[0]
        if count == 0:
            json_path = os.path.join(
                BASE_DIR,
                "core",
                "wallet_core",
                "test_wallets",
                "star_wars_wallets.json",
            )
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    if isinstance(data, Mapping):
                        wallets = data.get("wallets")
                        if not isinstance(wallets, list):
                            log.warning(
                                "⚠️ Wallet seed JSON missing 'wallets' list",
                                source="DataLocker",
                            )
                            return
                    elif isinstance(data, list):
                        wallets = data
                    else:
                        log.warning(
                            f"⚠️ Unexpected wallet seed structure: {type(data)}",
                            source="DataLocker",
                        )
                        return

                    for w in wallets:
                        if not isinstance(w, Mapping):
                            log.warning(
                                f"⚠️ Skipping invalid wallet entry {w!r}",
                                source="DataLocker",
                            )
                            continue
                        try:
                            self.wallets.create_wallet(dict(w))
                        except Exception as e:
                            log.warning(
                                f"Wallet seed failed for {w.get('name')}: {e}",
                                source="DataLocker",
                            )
                    log.debug(f"Wallets seeded from {json_path}", source="DataLocker")
                except Exception as e:
                    log.error(f"❌ Failed seeding wallets: {e}", source="DataLocker")
            else:
                log.error(
                    f"Wallet seed file not found at {json_path}",
                    source="DataLocker",
                )

    def _seed_thresholds_if_empty(self):
        """Seed alert_thresholds table with defaults if empty."""
        cursor = self.db.get_cursor()
        if not cursor:
            log.error("❌ DB unavailable, skipping threshold seed", source="DataLocker")
            return
        count = cursor.execute("SELECT COUNT(*) FROM alert_thresholds").fetchone()[0]
        if count == 0:
            if AlertThresholdSeeder is None:
                log.warning(
                    "⚠️ AlertThresholdSeeder not available; skipping threshold seed",
                    source="DataLocker",
                )
                return
            try:
                seeder = AlertThresholdSeeder(self.db)
                created, updated = seeder.seed_all()
                log.debug(
                    f"Alert thresholds seeded: {created} created, {updated} updated",
                    source="DataLocker",
                )
            except Exception as e:
                log.error(
                    f"❌ Failed seeding alert thresholds: {e}", source="DataLocker"
                )

                try:
                    from system.death_nail_service import DeathNailService

                    # DeathNailService(log).trigger({
                    #     "message": "💀 Failed to seed alert thresholds",
                    #     "level": "HIGH",
                    #     "payload": {"error": str(e)},
                    # })
                    log.info(
                        "🔈 Death nail suppressed during alert seeding",
                        source="DataLocker",
                    )
                except Exception as death_e:
                    log.error(
                        f"❌ Death nail trigger failed: {death_e}",
                        source="DataLocker",
                    )

    def _ensure_travel_percent_threshold(self):
        """Add TravelPercent threshold if missing."""
        try:
            cursor = self.db.get_cursor()
            if not cursor:
                return
            count = cursor.execute(
                "SELECT COUNT(*) FROM alert_thresholds WHERE alert_type = 'TravelPercent'"
            ).fetchone()[0]
            if count:
                return

            from data.models import AlertThreshold
            from uuid import uuid4
            from datetime import datetime, timezone

            threshold = AlertThreshold(
                id=str(uuid4()),
                alert_type="TravelPercent",
                alert_class="Position",
                metric_key="travel_percent",
                condition="BELOW",
                low=50,
                medium=70,
                high=90,
                enabled=True,
                last_modified=datetime.now(timezone.utc).isoformat(),
                low_notify="Email",
                medium_notify="Email,SMS",
                high_notify="Email,SMS,Voice",
            )
            if DLThresholdManager is not None:
                DLThresholdManager(self.db).insert(threshold)
            else:  # pragma: no cover - optional dependency
                log.warning(
                    "⚠️ DLThresholdManager not available; skipping TravelPercent seed",
                    source="DataLocker",
                )
            log.debug("TravelPercent threshold seeded by ensure", source="DataLocker")
        except Exception as e:
            log.error(
                f"❌ Failed ensuring TravelPercent threshold: {e}",
                source="DataLocker",
            )

    def _seed_alerts_if_empty(self):
        """Seed the alerts table from sample_alerts.json if no alerts exist."""
        cursor = self.db.get_cursor()
        if not cursor:
            log.error("❌ DB unavailable, skipping alert seed", source="DataLocker")
            return

        count = cursor.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        if count != 0:
            return

        json_path = os.path.join(CONFIG_DIR, "sample_alerts.json")
        if not os.path.exists(json_path):
            log.warning(
                f"⚠️ sample_alerts.json not found at {json_path}; no alerts seeded",
                source="DataLocker",
            )
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                alerts = json.load(f)

            for alert in alerts:
                try:
                    self.alerts.create_alert(alert)
                except Exception as e:
                    log.warning(
                        f"Alert seed failed for {alert.get('id')}: {e}",
                        source="DataLocker",
                    )

            log.debug(
                f"Alerts seeded from {json_path}",
                source="DataLocker",
            )
        except Exception as e:
            log.error(f"❌ Failed seeding alerts: {e}", source="DataLocker")

    def _seed_alert_config_if_empty(self):
        """Seed global alert configuration from alert_thresholds.json if missing."""
        if self.system is None:
            log.warning(
                "⚠️ System data manager unavailable; skipping alert config seed",
                source="DataLocker",
            )
            return
        try:
            current = self.system.get_var("alert_thresholds")
            if current:
                return

            if not os.path.exists(ALERT_THRESHOLDS_PATH):
                log.warning(
                    f"⚠️ alert_thresholds.json not found at {ALERT_THRESHOLDS_PATH}; skipping seed",
                    source="DataLocker",
                )
                return

            with open(ALERT_THRESHOLDS_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)

            self.system.set_var("alert_thresholds", config)
            log.debug(
                "Alert config seeded from alert_thresholds.json",
                source="DataLocker",
            )
        except Exception as e:
            log.error(f"❌ Failed seeding alert config: {e}", source="DataLocker")

    def get_all_tables_as_dict(self) -> dict:
        """Return all user tables and their rows as a dictionary."""
        try:
            datasets = {}
            tables = self.db.list_tables()
            if not tables:
                return datasets
            for table in tables:
                datasets[table] = self.db.fetch_all(table)
            try:
                if self.hedges is not None:
                    hedge_rows = [vars(h) for h in self.hedges.get_hedges()]
                    if hedge_rows:
                        datasets["hedges"] = hedge_rows
            except Exception as e:  # pragma: no cover - optional enrichment
                log.error(f"❌ Failed to gather hedges: {e}", source="DataLocker")
            return datasets
        except Exception as e:
            log.error(f"❌ Failed to gather tables: {e}", source="DataLocker")
            return {}

    def read_table(self, name: str, limit: int = 200) -> list:
        """Convenience wrapper for ``DatabaseManager.read_table``."""
        return self.db.read_table(name, limit)
