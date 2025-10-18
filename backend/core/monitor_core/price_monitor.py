import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from backend.core.market_core.price_sync_service import PriceSyncService
from backend.data.data_locker import DataLocker
from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.core.monitor_core.monitor_service import MonitorService
from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log
from backend.core.reporting_core.config import PRICE_TTL_SECONDS
from backend.core.config_core import sonic_config_bridge as C


class PriceMonitor(BaseMonitor):
    """
    Fetches prices from external APIs and stores them in DB.
    Uses CoinGecko via MonitorService.
    """

    def __init__(self):
        super().__init__(
            name="price_monitor",
            ledger_filename="price_ledger.json",  # still optional, safe to retain
            timer_config_path=None  # leave in for compatibility
        )
        self.dl = DataLocker(str(MOTHER_DB_PATH))
        self.service = MonitorService()
        self._last_cycle_sync: Optional[datetime] = None

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _force_sync_requested() -> bool:
        return C.should_force_price_sync()

    def mark_cycle_synced(self, when: Optional[datetime] = None) -> None:
        """Record that prices were synced during the current Sonic cycle."""
        self._last_cycle_sync = when or self._utcnow()

    def _latest_price_timestamp(self) -> Optional[datetime]:
        try:
            cursor = self.dl.db.get_cursor()
            if cursor is None:
                return None
            cursor.execute("SELECT MAX(last_update_time) FROM prices")
            row = cursor.fetchone()
            if not row:
                return None
            ts = row[0]
            if ts in (None, ""):
                return None
            return datetime.fromtimestamp(float(ts), timezone.utc)
        except Exception as exc:
            log.debug(f"Failed to determine latest price timestamp: {exc}", source=self.name)
            return None

    def _is_fresh(self, ts: Optional[datetime]) -> bool:
        if ts is None or PRICE_TTL_SECONDS <= 0:
            return False
        try:
            age = (self._utcnow() - ts).total_seconds()
        except Exception:
            return False
        return age < PRICE_TTL_SECONDS

    def _should_skip_sync(self) -> bool:
        if self._force_sync_requested():
            return False
        if self._is_fresh(self._last_cycle_sync):
            return True
        return self._is_fresh(self._latest_price_timestamp())

    def _do_work(self):
        if self._should_skip_sync():
            log.info("⏭ Price data fresh; skipping sync", source=self.name)
            return {"skipped": True, "reason": "fresh"}

        result = PriceSyncService(self.dl).run_full_price_sync(source="price_monitor")
        if isinstance(result, dict):
            if result.get("success"):
                self.mark_cycle_synced()
            result.setdefault("skipped", False)
        return result


if __name__ == "__main__":
    log.banner("🚀 SELF-RUN: PriceMonitor")

    monitor = PriceMonitor()
    result = monitor.run_cycle()

    log.success("🧾 PriceMonitor Run Complete", source="SelfTest", payload=result)
