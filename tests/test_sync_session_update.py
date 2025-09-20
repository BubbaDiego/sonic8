import os
import sys
import types

try:  # pragma: no cover - prefer real dependency when available
    import solders  # type: ignore
    try:
        from solders.keypair import Keypair as _Keypair  # noqa: F401 - ensure importable
    except ModuleNotFoundError:
        raise
except ModuleNotFoundError:  # pragma: no cover - provide lightweight stub
    solders = types.ModuleType("solders")  # type: ignore[assignment]
    sys.modules.setdefault("solders", solders)

    class _DummyKeypair:
        @staticmethod
        def from_seed(seed):
            return _DummyKeypair()

        @staticmethod
        def from_bytes(data):
            return _DummyKeypair()

        def pubkey(self):
            class _DummyPubkey:
                def __str__(self):
                    return "DummyPubkey"

            return _DummyPubkey()

    keypair_mod = types.ModuleType("solders.keypair")
    keypair_mod.Keypair = _DummyKeypair
    solders.keypair = keypair_mod  # type: ignore[attr-defined]
    sys.modules.setdefault("solders.keypair", keypair_mod)

import pytest
from backend.data.data_locker import DataLocker
from backend.core.positions_core.position_sync_service import PositionSyncService
import core.core_constants as const

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
    def read(self, *a, **k):  # pragma: no cover - stub for file reads
        return ""

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

    monkeypatch.setattr(
        PositionSyncService,
        "update_jupiter_positions",
        lambda self: {"imported": 0, "updated": 0, "skipped": 0, "errors": 0, "position_ids": ["p1"]},
    )
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
    assert session is not None
    assert session.current_session_value >= 0.0
    assert session.session_performance_value >= 0.0


def test_update_positions_normalizes_wallet_address(tmp_path, monkeypatch):
    db = setup_db(tmp_path, monkeypatch)
    dl = init_locker(db)

    normalized = "CzRz9n1XG5G7F4Nvz9DL2yJ1k63HgNbUs8PR8VYi24rT"
    noisy_addr = f"# GPT address={normalized} base58=should_ignore"
    invalid_addr = "http://example.com/no-base58-here"

    dl.create_wallet({"name": "Noisy", "public_address": noisy_addr, "is_active": True})
    dl.create_wallet({"name": "Invalid", "public_address": invalid_addr, "is_active": True})

    captured_urls = []

    class DummyResponse:
        def json(self):
            return {"dataList": []}

    def fake_request(self, url, attempts=3, delay=1.0):
        captured_urls.append(url)
        return DummyResponse()

    monkeypatch.setattr(PositionSyncService, "_request_with_retries", fake_request)

    import backend.core.positions_core.position_sync_service as svc_module

    def _raise_signer_error():
        raise RuntimeError("no signer available")

    monkeypatch.setattr(svc_module, "load_signer", _raise_signer_error)

    service = PositionSyncService(dl)
    base = service._pick_api_base()

    summary = service.update_jupiter_positions()

    expected_url = f"{base}/v1/positions?walletAddress={normalized}&showTpslRequests=true"
    assert captured_urls == [expected_url]
    assert summary["imported"] == 0
    assert summary["updated"] == 0
    assert summary["errors"] == 0
