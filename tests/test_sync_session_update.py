import os
import sys
import types
import pytest
from backend.data.data_locker import DataLocker
from backend.core.positions_core.position_sync_service import PositionSyncService
import core.constants as const
import core.core_imports as ci

SEED_PATCHES = [
    "_seed_modifiers_if_empty",
    "_seed_wallets_if_empty",
    "_seed_thresholds_if_empty",
    "_seed_alerts_if_empty",
]

class DummyFile:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass
    def write(self, data):
        pass

class DummyHM:
    def __init__(self, positions):
        pass
    def get_hedges(self):
        return []

class DummyLedger:
    def __init__(self, db):
        pass
    def insert_ledger_entry(self, *a, **k):
        pass

def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "sync.db"
    os.environ["MOTHER_DB_PATH"] = str(db_path)
    const.MOTHER_DB_PATH = db_path
    const.DB_PATH = db_path
    ci.MOTHER_DB_PATH = db_path
    ci.DB_PATH = db_path
    for attr in SEED_PATCHES:
        monkeypatch.setattr(DataLocker, attr, lambda self: None)
    return db_path


def init_locker(db_path):
    return DataLocker.get_instance(str(db_path))


def test_run_full_sync_updates_session(tmp_path, monkeypatch):
    db = setup_db(tmp_path, monkeypatch)
    dl = init_locker(db)
    dl.create_wallet({"name": "W", "public_address": "addr", "is_active": True})
    dl.positions.create_position({
        "id": "p1",
        "wallet_name": "W",
        "asset_type": "BTC",
        "position_type": "long",
        "entry_price": 1.0,
        "liquidation_price": 0.0,
        "collateral": 0.0,
        "size": 1.0,
        "leverage": 1.0,
        "value": 30.0,
        "status": "ACTIVE",
    })
    dl.session.start_session(start_value=10.0, goal_value=40.0)

    monkeypatch.setattr(PositionSyncService, "update_jupiter_positions", lambda self: {"imported": 0, "updated": 0, "skipped": 0, "errors": 0})
    import backend.core.positions_core.position_sync_service as svc_module
    hedge_mod = types.ModuleType("positions.hedge_manager")
    hedge_mod.HedgeManager = DummyHM
    monkeypatch.setitem(sys.modules, "positions.hedge_manager", hedge_mod)
    ledger_mod = types.ModuleType("data.dl_monitor_ledger")
    ledger_mod.DLMonitorLedgerManager = DummyLedger
    monkeypatch.setitem(sys.modules, "data.dl_monitor_ledger", ledger_mod)
    monkeypatch.setattr(svc_module.os, "makedirs", lambda *a, **k: None)
    monkeypatch.setattr(svc_module.os, "listdir", lambda *a, **k: [])
    monkeypatch.setattr(svc_module.os, "remove", lambda *a, **k: None)
    monkeypatch.setattr(sys.modules['builtins'], "open", lambda *a, **k: DummyFile())

    service = PositionSyncService(dl)
    service.run_full_jupiter_sync()

    session = dl.session.get_active_session()
    assert session.current_session_value == pytest.approx(20.0)
    assert session.session_performance_value == pytest.approx(20.0)
