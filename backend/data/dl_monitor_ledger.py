import sqlite3
import json
import uuid
from datetime import datetime, timezone
from backend.core.logging import log
from backend.models.monitor_status import (
    MonitorStatus,
    MonitorType,
    MonitorHealth,
    MonitorDetail,

)

class DLMonitorLedgerManager:
    def __init__(self, db):
        self.db = db
        self.ensure_table()

    def ensure_table(self):
        cursor = self.db.get_cursor()
        if not cursor:
            log.error("❌ DB unavailable, ledger table not created", source="DLMonitorLedger")
            return
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitor_ledger (
                id TEXT PRIMARY KEY,
                monitor_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.commit()
        log.debug("monitor_ledger table ensured", source="DLMonitorLedger")

    def insert_ledger_entry(self, monitor_name: str, status: str, metadata: dict = None):
        import uuid
        import json

        entry = {
            "id": str(uuid.uuid4()),
            "monitor_name": monitor_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "metadata": json.dumps(metadata or {})
        }


        cursor = self.db.get_cursor()
        if not cursor:
            log.error("❌ DB unavailable, ledger entry not stored", source="DLMonitorLedger")
            return
        cursor.execute("""
            INSERT INTO monitor_ledger (
                id, monitor_name, timestamp, status, metadata
            ) VALUES (
                :id, :monitor_name, :timestamp, :status, :metadata
            )
        """, entry)
        self.db.commit()
        log.success(f"🧾 Ledger written to DB for {monitor_name}", source="DLMonitorLedger")

    def get_last_entry(self, monitor_name: str) -> dict:
        cursor = self.db.get_cursor()
        if not cursor:
            log.error("❌ DB unavailable, cannot fetch ledger entry", source="DLMonitorLedger")
            return {}
        cursor.execute("""
            SELECT timestamp, status, metadata
            FROM monitor_ledger
            WHERE monitor_name = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (monitor_name,))

        row = cursor.fetchone()

        if not row:
            return {}
        result = {
            "timestamp": row[0],
            "status": row[1],
            "metadata": row[2]
        }
        return result

    def get_status(self, monitor_name: str) -> dict:

        entry = self.get_last_entry(monitor_name)
        if not entry or not entry.get("timestamp"):
            return {"last_timestamp": None, "age_seconds": 9999}

        try:
            raw_ts = entry["timestamp"]
            if raw_ts.endswith("Z"):
                raw_ts = raw_ts.replace("Z", "+00:00")
            last_ts = datetime.fromisoformat(raw_ts)
            now = datetime.now(timezone.utc)
            age = (now - last_ts).total_seconds()
            return {
                "last_timestamp": last_ts.isoformat(),
                "age_seconds": round(age),
                "status": entry.get("status", "Unknown")
            }
        except Exception as e:
            log.error(f"🧨 Failed to parse timestamp for {monitor_name}: {e}", source="DLMonitorLedger")
            return {"last_timestamp": None, "age_seconds": 9999}



    def get_monitor_status_summary(self) -> MonitorStatus:

        """Return a MonitorStatus populated with the latest ledger info."""
        summary = MonitorStatus()
        mapping = {


        """Return a MonitorStatus snapshot for key monitors."""

        summary = MonitorStatus()

        monitor_map = {


            "sonic_monitor": MonitorType.SONIC,
            "price_monitor": MonitorType.PRICE,
            "position_monitor": MonitorType.POSITIONS,
            "xcom_monitor": MonitorType.XCOM,
        }

        for name, mtype in mapping.items():
            status_data = self.get_status(name)
            ts_raw = status_data.get("last_timestamp")
            ts = None
            if ts_raw:
                if ts_raw.endswith("Z"):
                    ts_raw = ts_raw.replace("Z", "+00:00")
                try:
                    ts = datetime.fromisoformat(ts_raw)
                except Exception:
                    ts = None

            if ts is None:
                health = MonitorHealth.OFFLINE
            else:
                status_str = (status_data.get("status") or "").lower()
                if status_str == "success":
                    health = MonitorHealth.HEALTHY
                elif status_str == "error":
                    health = MonitorHealth.ERROR
                else:
                    health = MonitorHealth.WARNING

            summary.monitors[mtype] = MonitorDetail(
                status=health,
                last_updated=ts,
                metadata={},
            )

        for name, mtype in monitor_map.items():
            info = self.get_status(name)
            status_str = str(info.get("status", "")).lower()
            health = (
                MonitorHealth.HEALTHY
                if status_str == "success"
                else MonitorHealth.ERROR
            )
            summary.update_monitor(mtype, health, metadata=info)

        for name, mtype in name_map.items():
            entry = self.get_last_entry(name)
            if not entry:
                continue

            status_str = (entry.get("status") or "").strip()
            metadata = entry.get("metadata")
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}

            health = MonitorHealth.WARNING
            status_lower = status_str.lower()
            if status_lower == "success":
                health = MonitorHealth.HEALTHY
            elif status_lower in {"error", "failed"}:
                health = MonitorHealth.ERROR

            summary.update_monitor(mtype, health, metadata)

            ts = entry.get("timestamp")
            if ts:
                try:
                    if ts.endswith("Z"):
                        ts = ts.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(ts)
                    summary.monitors[mtype].last_updated = dt
                except Exception as exc:  # pragma: no cover - log parse issues
                    log.error(
                        f"🧨 Failed to parse timestamp for {name}: {exc}",
                        source="DLMonitorLedger",
                    )



        return summary

