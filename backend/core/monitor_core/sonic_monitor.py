import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import asyncio
import logging
import time
from datetime import datetime, timezone
from backend.core.cyclone_core.cyclone_engine import Cyclone

from data.data_locker import DataLocker
from core.core_constants import MOTHER_DB_PATH

MONITOR_NAME = "sonic_monitor"
DEFAULT_INTERVAL = 60  # fallback if nothing set in DB

def get_monitor_interval(db_path=MOTHER_DB_PATH, monitor_name=MONITOR_NAME):
    dl = DataLocker(str(db_path))
    cursor = dl.db.get_cursor()
    if not cursor:
        logging.error("No DB cursor available; using default interval")
        return DEFAULT_INTERVAL
    cursor.execute(
        "SELECT interval_seconds FROM monitor_heartbeat WHERE monitor_name = ?",
        (monitor_name,),
    )
    row = cursor.fetchone()
    if row and row[0]:
        try:
            return int(row[0])
        except Exception:
            pass
    return DEFAULT_INTERVAL


def update_heartbeat(monitor_name, interval_seconds, db_path=MOTHER_DB_PATH):
    dl = DataLocker(str(db_path))
    cursor = dl.db.get_cursor()
    if not cursor:
        logging.error("No DB cursor available; heartbeat not recorded")
        return

    timestamp = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO monitor_heartbeat (monitor_name, last_run, interval_seconds)
        VALUES (?, ?, ?)
        ON CONFLICT(monitor_name) DO UPDATE
            SET last_run = excluded.last_run,
                interval_seconds = excluded.interval_seconds
        """,
        (monitor_name, timestamp, interval_seconds),
    )
    dl.db.commit()


def write_ledger(status: str, metadata: dict | None = None, db_path=MOTHER_DB_PATH):
    dl = DataLocker(str(db_path))
    try:
        dl.ledger.insert_ledger_entry(MONITOR_NAME, status=status, metadata=metadata)
    except Exception as exc:  # pragma: no cover - log ledger failures
        logging.error(f"Failed to write ledger entry: {exc}")


def heartbeat(loop_counter: int):
    timestamp = datetime.now(timezone.utc).isoformat()
    logging.info("❤️ SonicMonitor heartbeat #%d at %s", loop_counter, timestamp)


async def sonic_cycle(loop_counter: int, cyclone: Cyclone):
    """Run a full Cyclone cycle and then execute key monitors."""
    logging.info("🔄 SonicMonitor cycle #%d starting", loop_counter)

    # Execute the complete Cyclone pipeline
    await cyclone.run_cycle()

    # Run price, profit and risk monitors after the Cyclone cycle
    await asyncio.to_thread(cyclone.monitor_core.run_by_name, "price_monitor")
    await asyncio.to_thread(cyclone.monitor_core.run_by_name, "profit_monitor")
   # await asyncio.to_thread(cyclone.monitor_core.run_by_name, "risk_monitor")
    await asyncio.to_thread(cyclone.monitor_core.run_by_name, "liquid_monitor")

    # Alert V2 pipeline disabled

    heartbeat(loop_counter)
    logging.info("✅ SonicMonitor cycle #%d complete", loop_counter)


def main():
    loop_counter = 00000000000000000

    from backend.core.monitor_core.monitor_core import MonitorCore

    monitor_core = MonitorCore()
    cyclone = Cyclone(monitor_core=monitor_core)

    # --- Ensure the heartbeat table exists ---
    dl = DataLocker(str(MOTHER_DB_PATH))
    cursor = dl.db.get_cursor()
    if not cursor:
        logging.error("No DB cursor available; cannot initialize heartbeat table")
        return
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS monitor_heartbeat (
            monitor_name TEXT PRIMARY KEY,
            last_run TIMESTAMP NOT NULL,
            interval_seconds INTEGER NOT NULL
        )
    """
    )
    dl.db.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        while True:
            # Always use the latest interval from the DB for max flexibility
            interval = get_monitor_interval()
            loop_counter += 1

            start_time = time.time()
            update_heartbeat(MONITOR_NAME, interval)
            try:
                loop.run_until_complete(sonic_cycle(loop_counter, cyclone))
                write_ledger("Success")
            except Exception as exc:
                logging.exception("SonicMonitor cycle failure")
                write_ledger("Error", {"error": str(exc)})
            finally:
                try:
                    status = dl.ledger.get_monitor_status_summary()
                    logging.debug("Monitor status summary: %s", status.json())
                except Exception:
                    logging.exception("Failed to update monitor status summary")

            elapsed = time.time() - start_time
            sleep_time = max(interval - elapsed, 0)
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        logging.info("SonicMonitor terminated by user.")


if __name__ == "__main__":
    main()
