# services/price_sync_service.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.core.logging import log
from backend.core.monitor_core.monitor_service import MonitorService
from backend.data.dl_monitor_ledger import DLMonitorLedgerManager
from datetime import datetime, timezone
from backend.core.reporting_core.task_events import (
    phase_end,
    phase_start,
)


class PriceSyncService:
    def __init__(self, data_locker):
        self.dl = data_locker
        self.service = MonitorService()

    def _cached_prices(self) -> dict[str, float]:
        try:
            price_mgr = getattr(self.dl, "prices", None)
            if not price_mgr:
                return {}
            rows = price_mgr.get_all_prices() or []
        except Exception:
            return {}

        fallback: dict[str, float] = {}
        for row in rows:
            if isinstance(row, dict):
                asset = row.get("asset_type") or row.get("asset")
                price = row.get("current_price") or row.get("price")
            else:
                asset = getattr(row, "asset_type", getattr(row, "asset", None))
                price = getattr(row, "current_price", getattr(row, "price", None))
            if not asset or price is None:
                continue
            try:
                fallback[str(asset).upper()] = float(price)
            except Exception:
                continue
        return fallback

    def run_full_price_sync(self, source="user") -> dict:
        from datetime import datetime, timezone
        from data.dl_monitor_ledger import DLMonitorLedgerManager

        log.banner("📈 Starting Price Sync")
        log.info("Initiating sync workflow...", source="PriceSyncService")
        phase_start("price_sync", "Starting Price Sync")

        try:
            now = datetime.now(timezone.utc)
            prices = self.service.fetch_prices()
            fallback_used = False

            if not prices:
                cached_prices = self._cached_prices()
                if cached_prices:
                    fallback_used = True
                    prices = cached_prices
                    log.warning(
                        "⚠️ Remote price fetch failed; using cached snapshot",
                        source="PriceSyncService",
                    )
                else:
                    log.warning("⚠️ No prices fetched", source="PriceSyncService")
                    result = {
                        "fetched_count": 0,
                        "assets": [],
                        "success": False,
                        "error": "No prices returned from service",
                        "timestamp": now.isoformat(),
                    }
                    self._write_ledger(result, "Error")
                    phase_end("price_sync", "warn", note="no prices returned")
                    return result

            asset_list = []
            for asset, price in prices.items():
                if price is None:
                    log.warning(f"No price for {asset}", source="PriceSyncService")
                    continue
                if not fallback_used:
                    if asset == "SPX":
                        self.dl.insert_or_update_price("SPX", price, source=source)
                    else:
                        self.dl.insert_or_update_price(asset, price, source=source)
                log.info(f"💾 Saved {asset} = ${price:,.4f}", source="PriceSyncService")
                try:
                    from backend.data.learning_database.learning_event_logger import (
                        log_learning_event,
                    )

                    payload = {
                        "asset_type": asset,
                        "price": price,
                    }
                    log_learning_event("price_ticks", payload)
                except Exception:
                    pass
                asset_list.append(asset)

            result = {
                "fetched_count": len(asset_list),
                "assets": asset_list,
                "success": not fallback_used,
                "timestamp": now.isoformat(),
            }
            if fallback_used:
                result["fallback"] = True
                result["error"] = "remote fetch failed; using cached snapshot"

            if fallback_used:
                log.warning(
                    "⚠️ Price sync completed using cached snapshot",
                    source="PriceSyncService",
                    payload={"count": len(asset_list)},
                )
            else:
                log.success("✅ Price sync complete", source="PriceSyncService", payload={
                    "count": len(prices),
                    "assets": asset_list,
                })

            ledger_status = "Success" if result["success"] else "Warn"
            self._write_ledger(result, ledger_status)
            log.banner("✅ Price Sync Completed")
            phase_note = f"{len(asset_list)} assets" if asset_list else "cached snapshot"
            verdict = "ok" if result["success"] else "warn"
            phase_end("price_sync", verdict, note=phase_note)
            return result

        except Exception as e:
            error_message = str(e)
            log.error(f"❌ Price sync failed: {error_message}", source="PriceSyncService")

            result = {
                "fetched_count": 0,
                "assets": [],
                "success": False,
                "error": error_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._write_ledger(result, "Error")
            phase_end("price_sync", "fail", note=error_message)
            return result

    def _write_ledger(self, result: dict, status: str):
        try:
            ledger = DLMonitorLedgerManager(self.dl.db)
            ledger.insert_ledger_entry("price_monitor", status, metadata=result)
            log.info("🧾 Price ledger updated", source="PriceSyncService")
        except Exception as e:
            log.warning(f"⚠️ Ledger write failed: {e}", source="PriceSyncService")

