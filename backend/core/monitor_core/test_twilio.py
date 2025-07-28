__test__ = False
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.data_locker import DataLocker
from xcom.xcom_core import XComCore
from core.core_constants import MOTHER_DB_PATH
from core.logging import log

# ---- NEW: Import your Flask app ----
try:
    from sonic_app import app   # Adjust import if needed
except Exception:  # pragma: no cover - optional dependency
    app = None

def run_test_call():
    # 📦 Load DataLocker + XComCore
    dl = DataLocker(MOTHER_DB_PATH)
    xcom = XComCore(dl.system)

    # 🧪 Send test HIGH-level notification (Voice + SMS + Sound)
    level = "HIGH"
    subject = "Test Voice Notification"
    body = "📞 This is a test voice call via Sonic XComCore."

    log.info("🔁 Dispatching XCom test via send_notification()", source="TestScript")
    result = xcom.send_notification(level, subject, body)

    print("Dispatch Result:", result)

if __name__ == "__main__":
    with app.app_context():
        run_test_call()
