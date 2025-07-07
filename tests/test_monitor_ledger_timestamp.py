import uuid
from datetime import datetime, timezone


def _insert_raw(dl, ts_str):
    cursor = dl.db.get_cursor()
    cursor.execute(
        "INSERT INTO monitor_ledger (id, monitor_name, timestamp, status, metadata) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), "test_monitor", ts_str, "Success", "{}"),
    )
    dl.db.commit()


def test_get_status_parses_timezone_aware(dl_tmp):
    aware_ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    _insert_raw(dl_tmp, aware_ts.isoformat())

    status = dl_tmp.ledger.get_status("test_monitor")
    assert status["last_timestamp"].startswith("2024-01-01T00:00:00")
    assert status["status"] == "Success"


def test_get_status_parses_naive_as_utc(dl_tmp):
    naive_ts = datetime(2024, 1, 2)  # no tzinfo
    _insert_raw(dl_tmp, naive_ts.isoformat())

    status = dl_tmp.ledger.get_status("test_monitor")
    assert status["last_timestamp"].startswith("2024-01-02T00:00:00")
    assert status["status"] == "Success"
