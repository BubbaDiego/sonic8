from fastapi.testclient import TestClient
from fastapi import FastAPI
import types
from datetime import datetime, timezone, timedelta
import sqlite3

from backend.routes.monitor_status_api import (
    router as monitor_status_router,
    reset_liquid_snooze,
)
from backend.deps import get_app_locker
from backend.data.data_locker import DataLocker
from backend.core.monitor_core import liquidation_monitor
from backend.core.xcom_core.voice_service import VoiceService
from backend.core.monitor_core import profit_monitor


def make_client(dl: DataLocker) -> TestClient:
    app = FastAPI()
    app.include_router(monitor_status_router)
    app.dependency_overrides[get_app_locker] = lambda: dl
    return TestClient(app)


def test_monitor_status_update(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    client = make_client(dl)

    resp = client.get("/api/monitor-status/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["monitors"]["Sonic Monitoring"]["status"] == "Offline"
    assert data["sonic_last_complete"] is None

    dl.ledger.insert_ledger_entry("sonic_monitor", status="Success", metadata={})

    resp = client.get("/api/monitor-status/")
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["sonic_last_complete"] is not None

    resp = client.get("/api/monitor-status/SONIC")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["status"] == "Healthy"


def test_liquid_snooze_countdown(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    # Ensure deterministic config with notifications disabled
    dl.system.set_var(
        "liquid_monitor",
        {
            "snooze_seconds": 60,
            "thresholds": {"BTC": 5.0},
            "notifications": {"system": False, "voice": False, "sms": False, "tts": False},
        },
    )

    # Patch monitor dependencies
    class FakePM:
        def get_active_positions(self):
            return [
                types.SimpleNamespace(
                    liquidation_distance=4.0,
                    asset_type="BTC",
                    position_type="LONG",
                    current_price=100.0,
                    liquidation_price=95.0,
                )
            ]

    monkeypatch.setattr(liquidation_monitor, "DLPositionManager", lambda db: FakePM())
    monkeypatch.setattr(
        liquidation_monitor,
        "XComCore",
        lambda _dl: types.SimpleNamespace(send_notification=lambda *a, **k: None),
    )

    monitor = liquidation_monitor.LiquidationMonitor()
    result = monitor._do_work()
    assert result["alert_sent"] is True

    client = make_client(dl)
    resp = client.get("/api/monitor-status/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["liquid_snooze"] > 0


def test_sonic_next_positive(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    cursor = dl.db.get_cursor()
    now = datetime.now(timezone.utc) - timedelta(seconds=1)
    cursor.execute(
        "INSERT INTO monitor_heartbeat (monitor_name, last_run, interval_seconds) VALUES (?, ?, ?)",
        ("sonic_monitor", now.isoformat(), 60),
    )
    dl.db.commit()

    client = make_client(dl)
    resp = client.get("/api/monitor-status/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sonic_next"] > 0


def test_monitor_status_handles_query_failure(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    def bad_cursor():
        class C:
            def execute(self, *a, **k):
                raise sqlite3.InterfaceError("boom")

            def fetchone(self):
                return None

            def close(self):
                pass

        return C()

    monkeypatch.setattr(dl.db, "get_cursor", bad_cursor)

    client = make_client(dl)
    resp = client.get("/api/monitor-status/")
    assert resp.status_code == 200


def test_reset_liquid_snooze(monkeypatch, tmp_path):
    """POSTing to reset-liquid-snooze clears the timestamp."""
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    # Pre-populate config with a snooze timestamp
    dl.system.set_var(
        "liquid_monitor",
        {
            "snooze_seconds": 60,
            "thresholds": {"BTC": 5.0},
            "notifications": {
                "system": False,
                "voice": False,
                "sms": False,
                "tts": False,
            },
            "_last_alert_ts": 1,
        },
    )

    # Avoid running the real monitor cycle
    monkeypatch.setattr(
        "backend.core.monitor_core.monitor_core.MonitorCore.run_by_name", lambda self, name: None
    )

    result = reset_liquid_snooze(dl)
    assert result == {"success": True}

    cfg = dl.system.get_var("liquid_monitor") or {}
    assert "_last_alert_ts" not in cfg


def test_profit_voice_updates_liquid_snooze(monkeypatch, tmp_path):
    """Profit monitor voice alerts should set liquidation snooze timer."""
    db_path = tmp_path / "test.db"
    dl = DataLocker(str(db_path))
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))

    dl.system.set_var(
        "liquid_monitor",
        {
            "snooze_seconds": 60,
            "thresholds": {"BTC": 5.0},
        },
    )

    dl.system.set_var(
        "profit_monitor",
        {
            "notifications": {
                "system": False,
                "voice": True,
                "sms": False,
                "tts": False,
            },
            "enabled": True,
        },
    )

    class FakePC:
        def __init__(self, _dl):
            pass

        def get_active_positions(self):
            return [types.SimpleNamespace(pnl_after_fees_usd=100.0)]

    class FakeThresholdSvc:
        def __init__(self, _db):
            pass

        def get_thresholds(self, *a, **k):
            return types.SimpleNamespace(low=0, medium=0, high=50)

    monkeypatch.setattr(profit_monitor, "DataLocker", lambda *_a, **_k: dl)
    monkeypatch.setattr(profit_monitor, "PositionCore", lambda _dl: FakePC(_dl))
    monkeypatch.setattr(profit_monitor, "ThresholdService", FakeThresholdSvc)
    monkeypatch.setattr(
        VoiceService,
        "call",
        lambda self, *a, **k: (True, "sid", "+10000000000", "+10000000001", 201),
    )

    monitor = profit_monitor.ProfitMonitor()
    result = monitor._do_work()
    assert result["alert_triggered"] is True

    client = make_client(dl)
    resp = client.get("/api/monitor-status/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["liquid_snooze"] > 0

