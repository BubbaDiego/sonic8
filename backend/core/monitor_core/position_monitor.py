import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.data.data_locker import DataLocker
from backend.core.positions_core.position_core import PositionCore
from backend.core.constants import MOTHER_DB_PATH
from datetime import datetime, timezone
from backend.core.logging import log

class PositionMonitor(BaseMonitor):
    """
    Actively syncs positions from Jupiter and logs summary.
    """
    def __init__(self):
        super().__init__(name="position_monitor", ledger_filename="position_ledger.json")
        self.dl = DataLocker(str(MOTHER_DB_PATH))
        self.core = PositionCore(self.dl)

    def _do_work(self):
        log.info("🔄 Starting position sync", source="PositionMonitor")
        sync_result = self.core.update_positions_from_jupiter(source="position_monitor")

        # 📦 Return key sync info for display/logging
        return {
            "imported": sync_result.get("imported", 0),
            "skipped": sync_result.get("skipped", 0),
            "errors": sync_result.get("errors", 0),
            "hedges": sync_result.get("hedges", 0),
            "timestamp": sync_result.get("timestamp", datetime.now(timezone.utc).isoformat())
        }

# ✅ Self-execute entrypoint
if __name__ == "__main__":
    log.banner("🚀 SELF-RUN: PositionMonitor")
    monitor = PositionMonitor()
    result = monitor.run_cycle()
    log.success("🧾 PositionMonitor Run Complete", source="SelfTest", payload=result)
    log.banner("✅ Position Sync Finished")
