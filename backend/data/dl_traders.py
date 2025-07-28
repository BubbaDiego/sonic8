"""Data access layer for :class:`Trader` records.

This module persists trader metadata in a simple SQLite table. Loaded
records are returned as :class:`Trader` objects with missing fields filled
automatically:

* ``born_on`` - Defaults to the ``created_at`` timestamp stored in the
  database if not present in the JSON payload.
* ``initial_collateral`` - Defaults to ``0.0`` when absent.
"""

import json
from dataclasses import asdict

from backend.models.trader import Trader

from backend.utils.time_utils import iso_utc_now, normalize_iso_timestamp

import os
from datetime import datetime
from backend.core.logging import log
from backend.core.core_constants import CONFIG_DIR

ACTIVE_TRADERS_JSON_PATH = CONFIG_DIR / "active_traders.json"



class DLTraderManager:
    def __init__(self, db):
        self.db = db
        self.last_error = None  # Message from most recent failure
        log.debug("DLTraderManager initialized.", source="DLTraderManager")
        self._initialize_table()

    def _initialize_table(self):
        cursor = self.db.get_cursor()
        if not cursor:
            log.error("❌ DB unavailable for trader table init", source="DLTraderManager")
            return
        log.debug("Ensuring 'traders' table exists...", source="DLTraderManager")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS traders (
                name TEXT PRIMARY KEY,
                trader_json TEXT NOT NULL,
                created_at TEXT,
                last_updated TEXT
            )
        """)
        self.db.commit()
        # Logging suppressed to reduce console noise

    def create_trader(self, trader: object) -> bool:
        """Persist a new trader record.

        Accepts either a :class:`Trader` instance or a mapping and returns
        ``True`` on success, ``False`` if any error occurs."""
        try:
            if isinstance(trader, Trader):
                trader = asdict(trader)
            name = trader.get("name")
            if not name:
                raise ValueError("Trader 'name' is required")
            log.debug("Creating trader", source="DLTraderManager", payload=trader)

            now = iso_utc_now()
            trader.setdefault("born_on", now)
            if "initial_collateral" not in trader:
                bal = trader.get("wallet_balance", 0.0)
                try:
                    bal = float(bal)
                except Exception:
                    bal = 0.0
                trader["initial_collateral"] = bal

            trader.setdefault("initial_collateral", 0.0)
            trader_json = json.dumps(trader, indent=2)

            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable for trader creation", source="DLTraderManager")
                return False

            cursor.execute(
                "INSERT OR REPLACE INTO traders (name, trader_json, created_at, last_updated) VALUES (?, ?, ?, ?)",
                (name, trader_json, now, now),
            )
            self.db.commit()
            log.success(f"✅ Trader created: {name}", source="DLTraderManager")
            return True
        except Exception as e:
            self.last_error = str(e)
            log.error(f"❌ Failed to create trader: {e}", source="DLTraderManager")
            return False

    def get_trader_by_name(self, name: str) -> Trader | None:
        """Return a :class:`Trader` by name with default fields filled in."""
        try:
            log.debug(
                f"Fetching trader by name: {name}", source="DLTraderManager"
            )
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while fetching trader", source="DLTraderManager")
                return None
            cursor.execute(
                "SELECT trader_json, created_at FROM traders WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            trader = json.loads(row["trader_json"]) if row else None

            if trader is not None:
                # Fill defaults from DB metadata when missing
                if "born_on" not in trader:
                    trader["born_on"] = normalize_iso_timestamp(row["created_at"])
                trader.setdefault("initial_collateral", 0.0)
                trader.setdefault("strategy_notes", "")
            log.debug(
                "Trader loaded", source="DLTraderManager", payload=trader or {})

            if trader is not None and "born_on" not in trader:
                trader["born_on"] = normalize_iso_timestamp(row["created_at"])
            log.debug("Trader loaded", source="DLTraderManager", payload=trader or {})

            return Trader(**trader) if trader is not None else None
        except Exception as e:
            log.error(f"❌ Failed to retrieve trader '{name}': {e}", source="DLTraderManager")
            return None

    def list_traders(self) -> list[Trader]:
        """Return all traders with defaults applied."""
        try:
            log.debug("Fetching traders from DB...", source="DLTraderManager")
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while listing traders", source="DLTraderManager")
                return []
            cursor.execute("SELECT trader_json, created_at FROM traders")
            rows = cursor.fetchall()
            traders: list[Trader] = []
            for row in rows:

                trader = json.loads(row["trader_json"])
                if "born_on" not in trader:
                    trader["born_on"] = normalize_iso_timestamp(row["created_at"])
                trader.setdefault("initial_collateral", 0.0)
                trader.setdefault("strategy_notes", "")
                traders.append(Trader(**trader))
            log.debug(
                f"Loaded {len(traders)} traders from DB", source="DLTraderManager"
            )
            return traders
        except Exception as e:
            log.error(f"❌ Failed to list traders: {e}", source="DLTraderManager")
            return []

    def update_trader(self, name: str, fields: dict):
        try:
            log.debug(f"Attempting update on trader: {name}", source="DLTraderManager", payload=fields)
            trader = self.get_trader_by_name(name)
            if not trader:
                log.warning(f"⚠️ Trader not found for update: {name}", source="DLTraderManager")
                return

            if isinstance(trader, Trader):
                for k, v in fields.items():
                    setattr(trader, k, v)
                trader_json = json.dumps(asdict(trader), indent=2)
            else:
                trader.update(fields)
                trader_json = json.dumps(trader, indent=2)
            now = iso_utc_now()

            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while updating trader", source="DLTraderManager")
                return
            cursor.execute(
                "UPDATE traders SET trader_json = ?, last_updated = ? WHERE name = ?",
                (trader_json, now, name),
            )
            self.db.commit()
            log.success(f"🔄 Trader updated: {name}", source="DLTraderManager")
        except Exception as e:
            log.error(f"❌ Failed to update trader '{name}': {e}", source="DLTraderManager")

    def delete_trader(self, name: str):
        try:
            log.debug(f"Deleting trader: {name}", source="DLTraderManager")
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while deleting trader", source="DLTraderManager")
                raise RuntimeError("DB unavailable")
            cursor.execute("DELETE FROM traders WHERE name = ?", (name,))
            deleted = cursor.rowcount > 0
            self.db.commit()
            if deleted:
                log.info(f"🗑️ Trader deleted: {name}", source="DLTraderManager")
            else:
                log.warning(f"Trader not found for deletion: {name}", source="DLTraderManager")
            return deleted
        except Exception as e:
            log.error(f"❌ Failed to delete trader '{name}': {e}", source="DLTraderManager")
            raise

    def delete_all_traders(self):
        """Remove all trader records from the database."""
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while deleting all traders", source="DLTraderManager")
                return
            cursor.execute("DELETE FROM traders")
            self.db.commit()
            log.success("🧹 All traders deleted", source="DLTraderManager")
        except Exception as e:
            log.error(f"❌ Failed to delete all traders: {e}", source="DLTraderManager")

    def export_to_json(self, path: str = str(ACTIVE_TRADERS_JSON_PATH)) -> None:
        """Write all traders to a JSON file."""
        try:
            traders = self.list_traders()
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([asdict(t) for t in traders], fh, indent=2)
            log.info(f"💾 Traders exported to {path}", source="DLTraderManager")
        except Exception as e:
            log.error(f"❌ Failed to export traders: {e}", source="DLTraderManager")

    def import_from_json(self, path: str = str(ACTIVE_TRADERS_JSON_PATH)) -> int:
        """Import traders from a JSON file, replacing existing ones."""
        if not os.path.exists(path):
            return 0
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as e:
            log.error(f"❌ Failed to read traders JSON: {e}", source="DLTraderManager")
            return 0

        if not isinstance(data, list):
            return 0

        count = 0
        for item in data:
            if isinstance(item, dict) and item.get("name"):
                self.create_trader(item)
                count += 1

        log.success(
            f"Imported {count} traders from {path}", source="DLTraderManager"
        )
        return count

    def quick_import_from_wallets(self) -> bool:
        """Create traders from active wallets whose names match a persona."""
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable for quick import", source="DLTraderManager")
                return False

            cursor.execute("SELECT name, balance, is_active FROM wallets")
            wallets = [dict(row) for row in cursor.fetchall()]

            active = [w for w in wallets if w.get("is_active", 1)]

            from backend.core.oracle_core.persona_manager import PersonaManager
            from backend.core.trader_core.persona_avatars import AVATARS

            pm = PersonaManager()
            persona_names = list(pm.list_personas())

            created = 0
            for w in active:
                wname = w.get("name", "")
                match = next((p for p in persona_names if p.lower() in wname.lower()), None)
                if not match:
                    continue

                persona = pm.get(match)
                avatar_key = getattr(persona, "avatar", match)
                avatar = AVATARS.get(avatar_key, {}).get("icon", avatar_key)

                trader_data = {
                    "name": persona.name,
                    "avatar": avatar,
                    "color": getattr(persona, "color", ""),
                    "wallet": wname,
                    "born_on": iso_utc_now(),
                    "wallet_balance": w.get("balance", 0.0),
                    "initial_collateral": w.get("balance", 0.0),
                }

                if self.create_trader(trader_data):
                    created += 1

            log.success(
                f"Quick import created {created} traders", source="DLTraderManager"
            )
            return created > 0
        except Exception as e:
            log.error(
                f"❌ Failed quick import from wallets: {e}", source="DLTraderManager"
            )
            return False

