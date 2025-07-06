import uuid
from datetime import datetime, timezone

import pytest

from data.data_locker import DataLocker
from backend.data.dl_monitor_ledger import DLMonitorLedgerManager
from backend.models.monitor_status import MonitorType, MonitorHealth


def insert_entry(dl, name, status, ts):
    cursor = dl.db.get_cursor()
    cursor.execute(
        "INSERT INTO monitor_ledger (id, monitor_name, timestamp, status, metadata) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), name, ts.isoformat(), status, "{}"),
    )
    dl.db.commit()


def test_get_monitor_status_summary(dl_tmp):
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    insert_entry(dl_tmp, "sonic_monitor", "Success", now)
    insert_entry(dl_tmp, "price_monitor", "Error", now)
    insert_entry(dl_tmp, "position_monitor", "Success", now)
    insert_entry(dl_tmp, "xcom_monitor", "Success", now)

    summary = dl_tmp.ledger.get_monitor_status_summary()

    assert summary.monitors[MonitorType.SONIC].status is MonitorHealth.HEALTHY
    assert summary.monitors[MonitorType.PRICE].status is MonitorHealth.ERROR
    assert summary.monitors[MonitorType.POSITIONS].status is MonitorHealth.HEALTHY
    assert summary.monitors[MonitorType.XCOM].status is MonitorHealth.HEALTHY

    for detail in summary.monitors.values():
        assert detail.last_updated == now


def test_monitor_core_status_snapshot(monkeypatch, dl_tmp):
    now = datetime(2024, 1, 2, tzinfo=timezone.utc)
    insert_entry(dl_tmp, "sonic_monitor", "Success", now)
    insert_entry(dl_tmp, "price_monitor", "Success", now)
    insert_entry(dl_tmp, "position_monitor", "Error", now)
    insert_entry(dl_tmp, "xcom_monitor", "Success", now)

    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl_tmp))

    import sys, types
    dummy = types.SimpleNamespace(
        PriceMonitor=lambda: None,
        PositionMonitor=lambda: None,
        OperationsMonitor=lambda: None,
        XComMonitor=lambda: None,
        TwilioMonitor=lambda: None,
        ProfitMonitor=lambda: None,
        RiskMonitor=lambda: None,
    )
    for name in [
        "backend.core.monitor_core.price_monitor",
        "backend.core.monitor_core.position_monitor",
        "backend.core.monitor_core.operations_monitor",
        "backend.core.monitor_core.xcom_monitor",
        "backend.core.monitor_core.twilio_monitor",
        "backend.core.monitor_core.profit_monitor",
        "backend.core.monitor_core.risk_monitor",
    ]:
        monkeypatch.setitem(sys.modules, name, dummy)

    from backend.core.monitor_core.monitor_core import MonitorCore
    from backend.core.monitor_core.monitor_registry import MonitorRegistry
    core = MonitorCore(registry=MonitorRegistry())
    snapshot = core.get_status_snapshot()

    assert snapshot.monitors[MonitorType.POSITIONS].status is MonitorHealth.ERROR
    assert snapshot.monitors[MonitorType.SONIC].last_updated == now
