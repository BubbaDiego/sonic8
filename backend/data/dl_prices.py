# dl_prices.py
from uuid import uuid4
from datetime import datetime, timezone
from backend.core.logging import log

class DLPriceManager:
    def __init__(self, db):
        self.db = db
        log.debug("DLPriceManager initialized.", source="DLPriceManager")

    def insert_price(self, price_data: dict):
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable for price insert", source="DLPriceManager")
                return
            if "id" not in price_data:
                price_data["id"] = str(uuid4())
            if "last_update_time" not in price_data:
                price_data["last_update_time"] = datetime.now(timezone.utc).timestamp()
            else:
                price_data["last_update_time"] = float(price_data["last_update_time"])

            if "previous_update_time" in price_data and price_data["previous_update_time"] is not None:
                price_data["previous_update_time"] = float(price_data["previous_update_time"])

            cursor.execute("""
                INSERT INTO prices (
                    id, asset_type, current_price, previous_price,
                    last_update_time, previous_update_time, source
                ) VALUES (
                    :id, :asset_type, :current_price, :previous_price,
                    :last_update_time, :previous_update_time, :source
                )
            """, price_data)

            self.db.commit()
            log.success(f"Inserted price for {price_data['asset_type']}", source="DLPriceManager")
        except Exception as e:
            log.error(f"Failed to insert price: {e}", source="DLPriceManager")

    def get_latest_price(self, asset_type: str) -> dict:
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while fetching price", source="DLPriceManager")
                return {}
            cursor.execute(
                """
                SELECT * FROM prices
                WHERE asset_type = ?
                ORDER BY last_update_time DESC
                LIMIT 1
                """,
                (asset_type,),
            )
            row = cursor.fetchone()
            if not row:
                return {}
            result = dict(row)
            if result.get("last_update_time") is not None:
                result["last_update_time"] = float(result["last_update_time"])
            if result.get("previous_update_time") is not None:
                result["previous_update_time"] = float(result["previous_update_time"])
            return result
        except Exception as e:
            log.error(f"Error retrieving price for {asset_type}: {e}", source="DLPriceManager")
            return {}

    def get_all_prices(self) -> list:
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while retrieving prices", source="DLPriceManager")
                return []
            cursor.execute("SELECT * FROM prices ORDER BY last_update_time DESC")
            rows = cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                if d.get("last_update_time") is not None:
                    d["last_update_time"] = float(d["last_update_time"])
                if d.get("previous_update_time") is not None:
                    d["previous_update_time"] = float(d["previous_update_time"])
                result.append(d)
            return result
        except Exception as e:
            log.error(f"Failed to retrieve all prices: {e}", source="DLPriceManager")
            return []

    def clear_prices(self):
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable, cannot clear prices", source="DLPriceManager")
                return
            cursor.execute("DELETE FROM prices")
            self.db.commit()
            log.warning("🧹 All price entries cleared.", source="DLPriceManager")
        except Exception as e:
            log.error(f"Failed to clear prices: {e}", source="DLPriceManager")

