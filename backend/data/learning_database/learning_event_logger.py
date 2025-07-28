"""Helper to insert telemetry rows into learning.db"""
import os
import uuid
from datetime import datetime
from backend.utils.time_utils import PACIFIC_TZ
from backend.core.logging import log
from backend.data.learning_database.learning_data_locker import LearningDataLocker

SAMPLING_SEC = int(os.getenv("LEARNING_SAMPLING_SEC", "60"))

_last_ts_cache = {}

def _should_sample(key: str) -> bool:
    now = datetime.utcnow().timestamp()
    last = _last_ts_cache.get(key, 0)
    if now - last >= SAMPLING_SEC:
        _last_ts_cache[key] = now
        return True
    return False

def log_learning_event(table: str, payload: dict) -> None:
    key = f"{table}:{payload.get('position_id') or payload.get('hedge_id') or payload.get('alert_id') or payload.get('trader_name')}"
    if not _should_sample(key):
        return
    dl = LearningDataLocker.get_instance()
    try:
        cursor = dl.db.get_cursor()
        payload = dict(payload)
        uid_field = {
            "position_events": "event_id",
            "hedge_events": "event_id",
            "price_ticks": "tick_id",
            "alert_events": "event_id",
            "trader_snapshots": "snapshot_id",
        }[table]
        payload.setdefault(uid_field, str(uuid.uuid4()))
        payload.setdefault("ts", datetime.now(PACIFIC_TZ).isoformat())
        cols = ", ".join(payload.keys())
        placeholders = ", ".join(f":{k}" for k in payload.keys())
        cursor.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", payload)
        dl.db.commit()
        log.debug(f"Learning event logged: {table}", source="LearningEventLogger")
    except Exception as e:
        if "no such table" in str(e).lower():
            try:
                dl.initialize_database()
                cursor = dl.db.get_cursor()
                cursor.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", payload)
                dl.db.commit()
                log.debug(
                    f"Learning DB auto-initialized, inserted {table}",
                    source="LearningEventLogger",
                )
                return
            except Exception as e2:
                e = e2
        log.error(
            f"Learning DB insert failed ({table}): {e}",
            source="LearningEventLogger",
            payload=payload,
        )
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/learning_db_failed_inserts.log", "a") as fh:
                fh.write(
                    f"{datetime.now(PACIFIC_TZ).isoformat()} | {table} | {e} | {payload}\n"
                )
        except Exception as e2:  # pragma: no cover - logging failure shouldn't fail tests
            log.error(
                f"Failed to write learning insert log: {e2}",
                source="LearningEventLogger",
            )
