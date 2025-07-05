import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import json
from datetime import datetime
from backend.core.logging import log
from backend.core.calc_core.calc_services import CalcServices
import sqlite3


class CalculationCore:
    def __init__(self, data_locker):
        self.data_locker = data_locker
        self.calc_services = CalcServices()
        self.modifiers = self._load_modifiers()

    def _load_modifiers(self):
        cursor = self.data_locker.db.get_cursor()
        if not cursor:
            log.error("❌ DB unavailable, using default modifiers", source="CalculationCore")
            weights = self.calc_services.weights
            return weights

        try:
            rows = cursor.execute(
                "SELECT key, value FROM modifiers WHERE group_name = 'heat_modifiers'"
            ).fetchall()
            weights = {row['key']: float(row['value']) for row in rows}
        except Exception as e:
            log.error(f"❌ Failed loading modifiers: {e}", source="CalculationCore")
            weights = {}

        if not weights:
            log.warning("⚠️ No modifiers found in DB; falling back to default", source="CalculationCore")
            weights = {
                "distanceWeight": 0.6,
                "leverageWeight": 0.3,
                "collateralWeight": 0.1
            }

        self.calc_services.weights = weights  # inject into CalcServices
        log.success("✅ Modifiers loaded into CalcServices", source="CalculationCore", payload=weights)
        return weights

    def get_heat_index(self, position: dict) -> float:
        return self.calc_services.calculate_composite_risk_index(position)

    def get_travel_percent(self, position_type, entry_price, current_price, liquidation_price):
        return self.calc_services.calculate_travel_percent(
            position_type, entry_price, current_price, liquidation_price
        )

    def aggregate_positions_and_update(self, positions: list, db_path: str) -> list:
        log.start_timer("aggregate_positions_and_update")
        log.info(
            "Starting aggregation on positions",
            source="aggregate_positions_and_update",
            payload={"count": len(positions)},
        )

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(positions);")
        db_columns = set(row[1] for row in cursor.fetchall())

        for pos in positions:
            data = self.calc_services._as_dict(pos)
            pos_id = data.get("id", "UNKNOWN")
            try:
                log.debug(
                    f"Aggregating position {pos_id}",
                    source="aggregate_positions_and_update",
                    payload=data,
                )

                position_type = (data.get("position_type") or "LONG").upper()
                entry_price = float(data.get("entry_price", 0.0))
                current_price = float(data.get("current_price", 0.0))
                liquidation_price = float(data.get("liquidation_price", 0.0))
                collateral = float(data.get("collateral", 0.0))
                size = float(data.get("size", 0.0))

                data["entry_price"] = entry_price
                data["current_price"] = current_price
                data["liquidation_price"] = liquidation_price
                data["collateral"] = collateral
                data["size"] = size

                data["travel_percent"] = self.calc_services.calculate_travel_percent(
                    position_type, entry_price, current_price, liquidation_price
                )
                data["liquidation_distance"] = self.calc_services.calculate_liquid_distance(current_price, liquidation_price)

                data["value"] = self.calc_services.calculate_value(data)
                data["pnl_after_fees_usd"] = self.calc_services.calculate_profit(data)
                data.setdefault("leverage", round(size / collateral, 2) if collateral > 0 else 0.0)
                heat_index = self.calc_services.calculate_composite_risk_index(data) or 0.0
                data["heat_index"] = data["current_heat_index"] = heat_index

                update_map = {}
                for key in db_columns:
                    if key == "id":
                        continue
                    if key in data:
                        update_map[key] = data[key]

                if not update_map:
                    continue

                set_clause = ", ".join(f"{k} = ?" for k in update_map.keys())
                params = list(update_map.values()) + [pos_id]
                cursor.execute(f"UPDATE positions SET {set_clause} WHERE id = ?", params)
                log.success(
                    "Updated DB for position",
                    source="aggregate_positions_and_update",
                    payload={"id": pos_id, "heat_index": heat_index},
                )

            except Exception as e:
                log.error(
                    f"Error processing position {pos_id}: {e}",
                    source="aggregate_positions_and_update",
                )

        conn.commit()
        conn.close()
        log.end_timer(
            "aggregate_positions_and_update",
            source="aggregate_positions_and_update",
        )
        return positions

    def set_modifier(self, key: str, value: float):
        cursor = self.data_locker.db.get_cursor()
        cursor.execute("""
            INSERT INTO modifiers (key, group_name, value, last_modified)
            VALUES (?, 'heat_modifiers', ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, last_modified = excluded.last_modified
        """, (key, value, datetime.now().isoformat()))
        self.data_locker.db.commit()
        self.modifiers[key] = value
        self.calc_services.weights[key] = value
        log.success(f"✅ Modifier updated: {key} = {value}", source="CalculationCore")

    def export_modifiers(self) -> str:
        return json.dumps({"heat_modifiers": self.modifiers}, indent=2)

    def import_modifiers(self, json_data: str):
        data = json.loads(json_data)
        heat_mods = data.get("heat_modifiers", {})
        for key, value in heat_mods.items():
            self.set_modifier(key, float(value))
        log.success("📦 Modifiers imported from JSON", source="CalculationCore")

    def calculate_totals(self, positions: list) -> dict:
        """Return aggregated totals for the provided positions."""
        return self.calc_services.calculate_totals(positions)
