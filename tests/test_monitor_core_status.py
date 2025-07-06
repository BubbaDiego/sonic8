from backend.core.monitor_core.monitor_core import MonitorCore
from backend.core.monitor_core.monitor_registry import MonitorRegistry
from backend.data.data_locker import DataLocker


def test_get_status_snapshot_returns_summary(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls, db_path=str(db_path): dl))

    dl.ledger.insert_ledger_entry("price_monitor", status="Success", metadata={"ok": True})
    dl.ledger.insert_ledger_entry("xcom_monitor", status="Error", metadata={"err": True})

    core = MonitorCore(registry=MonitorRegistry())
    summary = core.get_status_snapshot()

    assert summary == dl.ledger.get_monitor_status_summary()
