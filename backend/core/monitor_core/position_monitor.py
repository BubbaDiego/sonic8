import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.data.data_locker import DataLocker
from backend.core.positions_core.position_core import PositionCore
from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log
from backend.core.reporting_core.config import POSITIONS_TTL_SECONDS
from backend.core.config_core import sonic_config_bridge as C

class PositionMonitor(BaseMonitor):
    """
    Actively syncs positions from Jupiter and logs summary.
    """
    def __init__(self):
        super().__init__(name="position_monitor", ledger_filename="position_ledger.json")
        self.dl = DataLocker(str(MOTHER_DB_PATH))
        self.core = PositionCore(self.dl)
        self._last_cycle_sync: Optional[datetime] = None
        self._sync_in_progress = False

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _force_sync_requested() -> bool:
        return C.should_force_position_sync()

    def mark_cycle_synced(self, when: Optional[datetime] = None) -> None:
        """Record that positions were refreshed during the current Sonic cycle."""
        self._last_cycle_sync = when or self._utcnow()

    def _parse_timestamp(self, raw_ts: object) -> Optional[datetime]:
        if raw_ts in (None, "", 0):
            return None
        if isinstance(raw_ts, datetime):
            return raw_ts if raw_ts.tzinfo else raw_ts.replace(tzinfo=timezone.utc)
        if isinstance(raw_ts, (int, float)):
            try:
                return datetime.fromtimestamp(float(raw_ts), timezone.utc)
            except Exception:
                return None
        if isinstance(raw_ts, str):
            text = raw_ts.strip()
            if not text:
                return None
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                try:
                    return datetime.fromtimestamp(float(text), timezone.utc)
                except Exception:
                    return None
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return None

    def _latest_position_timestamp(self) -> Optional[datetime]:
        try:
            updates = self.dl.get_last_update_times()
            ts = updates.get("last_update_time_positions") if isinstance(updates, dict) else None
            parsed = self._parse_timestamp(ts)
            if parsed:
                return parsed
        except Exception as exc:
            log.debug(f"Failed to read system_vars timestamp: {exc}", source=self.name)

        # Fallback: inspect positions table for the newest "last_updated" column
        try:
            cursor = self.dl.db.get_cursor()
            if cursor is None:
                return None
            cursor.execute("SELECT last_updated FROM positions ORDER BY last_updated DESC LIMIT 1")
            row = cursor.fetchone()
            cursor.close()
            if not row:
                return None
            if isinstance(row, dict):
                value = row.get("last_updated")
            else:
                try:
                    value = row[0]
                except Exception:
                    value = None
            return self._parse_timestamp(value)
        except Exception as exc:
            log.debug(f"Failed to read latest position timestamp: {exc}", source=self.name)
            return None

    def _is_fresh(self, ts: Optional[datetime]) -> bool:
        if ts is None or POSITIONS_TTL_SECONDS <= 0:
            return False
        try:
            age = (self._utcnow() - ts).total_seconds()
        except Exception:
            return False
        return age < POSITIONS_TTL_SECONDS

    def _should_skip_sync(self) -> Tuple[bool, str]:
        if self._force_sync_requested():
            return False, ""
        if self._sync_in_progress:
            return True, "in-progress"
        if self._is_fresh(self._last_cycle_sync):
            return True, "cycle"
        if self._is_fresh(self._latest_position_timestamp()):
            return True, "fresh"
        return False, ""

    def _do_work(self):
        skip, reason = self._should_skip_sync()
        if skip:
            if reason == "cycle":
                note = "cycle"
            elif reason:
                note = reason
            else:
                note = "fresh"
            log.info(f"⏭ Position data {note}; skipping sync", source=self.name)
            return {"skipped": True, "reason": note}

        if self._sync_in_progress:
            return {"skipped": True, "reason": "in-progress"}

        log.info("🔄 Starting position sync", source="PositionMonitor")
        self._sync_in_progress = True
        try:
            sync_result = self.core.update_positions_from_jupiter(source="position_monitor")
        finally:
            self._sync_in_progress = False

        payload = {
            "imported": 0,
            "skipped": False,
            "errors": 0,
            "hedges": 0,
            "timestamp": self._utcnow().isoformat(),
        }

        if isinstance(sync_result, dict):
            payload.update(sync_result)
            if "timestamp" not in sync_result:
                payload["timestamp"] = self._utcnow().isoformat()
            payload.setdefault("skipped", False)

            success = sync_result.get("success")
            if success is None:
                errors = sync_result.get("errors")
                success = errors == 0 if errors is not None else True
        else:
            success = True

        if success:
            self.mark_cycle_synced()

        return payload

# ✅ Self-execute entrypoint
if __name__ == "__main__":
    log.banner("🚀 SELF-RUN: PositionMonitor")
    monitor = PositionMonitor()
    result = monitor.run_cycle()
    log.success("🧾 PositionMonitor Run Complete", source="SelfTest", payload=result)
    log.banner("✅ Position Sync Finished")
