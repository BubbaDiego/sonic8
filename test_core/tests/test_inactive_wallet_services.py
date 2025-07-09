import os
import sys
import types

import core.constants as const
import core.core_imports as ci
from data.data_locker import DataLocker
from backend.core.positions_core.position_core_service import PositionCoreService
from backend.core.positions_core.position_sync_service import PositionSyncService
from backend.core.wallet_core import WalletCore
from backend.models.portfolio import PortfolioSnapshot

SEED_PATCHES = [
    "_seed_modifiers_if_empty",
    "_seed_wallets_if_empty",
    "_seed_thresholds_if_empty",
    "_seed_alerts_if_empty",
]


def setup_db(tmp_path, monkeypatch, name="svc.db"):
    db_path = tmp_path / name
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


def test_position_core_service_snapshot_ignores_inactive(tmp_path, monkeypatch):
    db = setup_db(tmp_path, monkeypatch, "pcs.db")
    dl = init_locker(db)
    dl.create_wallet({"name": "active", "public_address": "a", "is_active": True})
    dl.create_wallet({"name": "inactive", "public_address": "b", "is_active": False})
    dl.positions.create_position({"id": "p1", "wallet_name": "active", "value": 5, "status": "ACTIVE"})
    dl.positions.create_position({"id": "p2", "wallet_name": "inactive", "value": 7, "status": "ACTIVE"})

    svc = PositionCoreService(dl)
    svc.record_positions_snapshot()
    snap = dl.portfolio.get_latest_snapshot()
    assert isinstance(snap, PortfolioSnapshot)
    assert snap.total_value == 5
    assert snap.total_long_size == 0.0
    assert snap.total_short_size == 0.0


def test_position_sync_service_snapshot_ignores_inactive(tmp_path, monkeypatch):
    db = setup_db(tmp_path, monkeypatch, "pss.db")
    dl = init_locker(db)
    dl.create_wallet({"name": "active", "public_address": "a", "is_active": True})
    dl.create_wallet({"name": "inactive", "public_address": "b", "is_active": False})
    dl.positions.create_position({"id": "p1", "wallet_name": "active", "value": 3, "status": "ACTIVE"})
    dl.positions.create_position({"id": "p2", "wallet_name": "inactive", "value": 7, "status": "ACTIVE"})

    monkeypatch.setattr(PositionSyncService, "update_jupiter_positions", lambda self: {"imported": 0, "updated": 0, "skipped": 0, "errors": 0})
    import backend.core.positions_core.position_sync_service as svc_module
    hedge_mod = types.ModuleType("positions.hedge_manager")
    hedge_mod.HedgeManager = DummyHM
    monkeypatch.setitem(sys.modules, "positions.hedge_manager", hedge_mod)
    dlmon_mod = types.ModuleType("data.dl_monitor_ledger")
    dlmon_mod.DLMonitorLedgerManager = DummyLedger
    monkeypatch.setitem(sys.modules, "data.dl_monitor_ledger", dlmon_mod)
    monkeypatch.setattr(svc_module.os, "makedirs", lambda *a, **k: None)
    monkeypatch.setattr(svc_module.os, "listdir", lambda *a, **k: [])
    monkeypatch.setattr(svc_module.os, "remove", lambda *a, **k: None)
    monkeypatch.setattr(sys.modules['builtins'], "open", lambda *a, **k: DummyFile())

    service = PositionSyncService(dl)
    service.run_full_jupiter_sync()
    snap = dl.portfolio.get_latest_snapshot()
    assert isinstance(snap, PortfolioSnapshot)
    assert snap.total_value == 3
    assert snap.total_long_size == 0.0
    assert snap.total_short_size == 0.0


def test_wallet_core_balance_ignores_inactive(tmp_path, monkeypatch):
    db = setup_db(tmp_path, monkeypatch, "wc.db")
    dl = init_locker(db)
    dl.create_wallet({"name": "active", "public_address": "a", "is_active": True})
    dl.create_wallet({"name": "inactive", "public_address": "b", "is_active": False})
    dl.positions.create_position({"wallet_name": "active", "value": 2, "status": "ACTIVE"})
    dl.positions.create_position({"wallet_name": "inactive", "value": 8, "status": "ACTIVE"})

    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls, db_path=str(db): dl))
    wc = WalletCore()
    assert wc.fetch_positions_balance("active") == 2
    assert wc.fetch_positions_balance("inactive") == 0
