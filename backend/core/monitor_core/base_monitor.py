import os
import traceback

from backend.core.logging import log
from backend.data.data_locker import DataLocker
from backend.core.core_constants import MOTHER_DB_PATH


class BaseMonitor:
    """Abstract base class for monitors with unified success/error logging."""

    # ------------------------------------------------------------------ #
    # Config flags
    # ------------------------------------------------------------------ #
    LOG_SUCCESS: bool = bool(int(os.getenv("MONITOR_LOG_SUCCESS", "0")))
    SUCCESS_LEVEL: str = "LOW"

    def __init__(self, name: str, ledger_filename: str = None, timer_config_path: str = None):
        self.name = name
        self.ledger_filename = ledger_filename
        self.timer_config_path = timer_config_path

    # ------------------------------------------------------------------ #
    # Notification helper
    # ------------------------------------------------------------------ #
    def _notify(self, level: str, subject: str, body: str, metadata=None) -> None:
        try:
            dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
            dl.notifications.insert(
                monitor=self.name,
                level=level,
                subject=subject,
                body=body,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - logging must not crash
            log.exception(exc, "Failed to write sonic_monitor_log row", source=self.name)

    def run_cycle(self):
        log.banner(f"🚀 Running {self.name}")
        result = {}
        status = "Success"
        try:
            result = self._do_work()

            if isinstance(result, dict):
                if "status" in result:
                    status = "Success" if str(result.get("status")).lower() == "success" else "Error"
                elif "success" in result:
                    status = "Success" if result.get("success") else "Error"
                elif "errors" in result:
                    status = "Success" if result.get("errors", 0) == 0 else "Error"
            

            # 🧾 Log to DB-backed ledger
            locker = DataLocker.get_instance(str(MOTHER_DB_PATH))
            locker.ledger.insert_ledger_entry(
                monitor_name=self.name,
                status=status,
                metadata=result
            )

            if status == "Success":
                log.success(f"{self.name} completed successfully.", source=self.name)
                if self.LOG_SUCCESS:
                    self._notify(
                        self.SUCCESS_LEVEL,
                        f"✅ {self.name} finished",
                        f"{self.name} completed successfully",
                        {"result": str(result)[:200]},
                    )
            return result
        except Exception as e:
            log.error(f"{self.name} failed: {e}", source=self.name)
            self._notify(
                "HIGH",
                f"❗ {self.name} error",
                str(e),
                {"trace": traceback.format_exc()[-1000:]},
            )

            # 🧾 Still write failure to DB ledger
            locker = DataLocker.get_instance(str(MOTHER_DB_PATH))
            locker.ledger.insert_ledger_entry(
                monitor_name=self.name,
                status="Error",
                metadata={"error": str(e)}
            )

            return None

    def _do_work(self):
        raise NotImplementedError("Monitors must implement `_do_work()`")
