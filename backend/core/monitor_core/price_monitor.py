import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from backend.core.market_core.price_sync_service import PriceSyncService
from backend.data.data_locker import DataLocker
from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.core.monitor_core.monitor_service import MonitorService
from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log


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



    def _do_work(self):
        return PriceSyncService(self.dl).run_full_price_sync(source="price_monitor")


if __name__ == "__main__":
    log.banner("🚀 SELF-RUN: PriceMonitor")

    monitor = PriceMonitor()
    result = monitor.run_cycle()

    log.success("🧾 PriceMonitor Run Complete", source="SelfTest", payload=result)
