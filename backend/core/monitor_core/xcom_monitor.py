import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.data.data_locker import DataLocker
from backend.core.xcom_core.xcom_core import XComCore
from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log


class XComMonitor(BaseMonitor):
    """Simple monitor to send a lightweight XCom notification."""

    def __init__(self):
        super().__init__(name="xcom_monitor", ledger_filename="xcom_ledger.json")
        self.dl = DataLocker(str(MOTHER_DB_PATH))
        self.xcom = XComCore(self.dl)

    def _do_work(self):
        log.info("📡 Sending XCom monitor ping", source="XComMonitor")
        result = self.xcom.send_notification(
            level="LOW",
            subject="XCom Monitor Ping",
            body="XCom monitor cycle notification",
            initiator="monitor"
        )
        return result
