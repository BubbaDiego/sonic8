import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.data.data_locker import DataLocker
from backend.core.xcom_core.xcom_config_service import XComConfigService
from backend.core.xcom_core.check_twilio_heartbeat_service import CheckTwilioHeartbeatService
from backend.core.core_constants import MOTHER_DB_PATH


class TwilioMonitor(BaseMonitor):
    """Heartbeat monitor to verify Twilio credentials."""

    def __init__(self):
        super().__init__(name="twilio_monitor", ledger_filename="twilio_ledger.json")
        self.dl = DataLocker(str(MOTHER_DB_PATH))
        self.config_service = XComConfigService(self.dl.system)

    def _do_work(self):
        cfg = self.config_service.get_provider("api") or {}
        service = CheckTwilioHeartbeatService(cfg)
        result = service.check(dry_run=True)
        return result

