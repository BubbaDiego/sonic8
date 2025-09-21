from __future__ import annotations

from datetime import datetime
import sqlite3
import sys
from types import ModuleType, SimpleNamespace
import json
import pytest

if "solders.keypair" not in sys.modules:  # pragma: no cover - lightweight stub
    solders_mod = ModuleType("solders")
    keypair_mod = ModuleType("solders.keypair")

    class _DummyPubkey:
        def __str__(self):
            return "StubPubkey"

    class _DummyKeypair:
        def __init__(self, pub=None):
            self._pub = pub or _DummyPubkey()

        @staticmethod
        def from_bytes(_):
            return _DummyKeypair()

        @staticmethod
        def from_seed(_):
            return _DummyKeypair()

        def pubkey(self):
            return self._pub

    keypair_mod.Keypair = _DummyKeypair
    solders_mod.keypair = keypair_mod
    sys.modules.setdefault("solders", solders_mod)
    sys.modules.setdefault("solders.keypair", keypair_mod)

# Some environments expose the service via positions.*, others via backend.*
try:  # pragma: no cover - keep compatibility with legacy module layout
    from positions.position_sync_service import PositionSyncService  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from backend.core.positions_core.position_sync_service import PositionSyncService
from backend.core.hedge_core.hedge_core import HedgeCore
from backend.core.trader_core.trader_update_service import TraderUpdateService


# -------------------------------------------------------------------------#
#                          ---  Stubs / Fakes  ---                         #
# -------------------------------------------------------------------------#
class _FakeDB:
    """Very small wrapper around sqlite3.Connection that mimics .get_cursor()."""

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._build_schema()

    def _build_schema(self):
        cur = self.conn.cursor()
        cur.execute(
            """CREATE TABLE positions (
                    id TEXT PRIMARY KEY,
                    asset_type TEXT,
                    position_type TEXT,
                    entry_price REAL,
                    liquidation_price REAL,
                    collateral REAL,
                    size REAL,
                    leverage REAL,
                    value REAL,
                    last_updated TEXT,
                    wallet_name TEXT,
                    pnl_after_fees_usd REAL,
                    travel_percent REAL,
                    current_price REAL,
                    heat_index REAL,
                    current_heat_index REAL,
                    liquidation_distance REAL,
                    stale INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'ACTIVE'
                )"""
        )
        self.conn.commit()

    def get_cursor(self):
        return self.conn.cursor()

    def commit(self):
        self.conn.commit()


class _FakePositionsFacade:
    def __init__(self, db):
        self.db = db

    def create_position(self, record, cursor_override=None):
        cur = cursor_override or self.db.get_cursor()
        keys = ",".join(record)
        qs = ",".join([":" + k for k in record])
        cur.execute(f"INSERT INTO positions ({keys}) VALUES ({qs})", record)
        if cursor_override is None:
            self.db.commit()

    def get_all_positions(self):
        cur = self.db.get_cursor()
        cur.execute("SELECT * FROM positions")
        return [dict(row) for row in cur.fetchall()]


class _FakeDataLocker(SimpleNamespace):
    def __init__(self):
        db = _FakeDB()
        wallet = {"is_active": True, "public_address": "WALLET_A", "name": "Wallet-A", "balance": 0.0}

        def read_wallets():
            return [wallet]

        def get_wallet_by_name(name):
            return wallet if name == wallet["name"] else None

        def update_wallet(name, data):
            if name == wallet["name"]:
                wallet.update(data)

        def get_latest_price(asset):
            return {"asset": asset, "current_price": 12.0}

        def read_positions():
            return []

        super().__init__(
            db=db,
            positions=_FakePositionsFacade(db),
            read_wallets=read_wallets,
            get_wallet_by_name=get_wallet_by_name,
            update_wallet=update_wallet,
            get_latest_price=get_latest_price,
            read_positions=read_positions,
            system=SimpleNamespace(
                set_last_update_times=lambda *a, **k: None
            ),
            portfolio=SimpleNamespace(record_snapshot=lambda *a, **k: None),
        )


# -------------------------------------------------------------------------#
#                               Fixtures                                   #
# -------------------------------------------------------------------------#
@pytest.fixture
def svc(monkeypatch):
    dl = _FakeDataLocker()
    dl.read_wallets()[0]["public_address"] = "5Egu5iBD5TvXPR7i5QazQi6JT51LZrq8P3dYRcM3wHz6"
    service = PositionSyncService(dl)

    # Patch network access – return canned Jupiter payload
    class _FakeResp:
        status_code = 200

        def json(self):
            return {
                "dataList": [
                    {
                        "positionPubkey": "pos_1",
                        "marketMint": "So11111111111111111111111111111111111111112",
                        "side": "long",
                        "entryPrice": 10,
                        "liquidationPrice": 5,
                        "collateral": 100,
                        "size": 0.1,
                        "leverage": 1,
                        "value": 100,
                        "updatedTime": datetime.now().timestamp(),
                        "pnlAfterFeesUsd": 2,
                        "pnlChangePctAfterFees": 0.02,
                        "markPrice": 12,
                    }
                ]
            }

        text = "{}"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(service, "_request_with_retries", lambda *_a, **_k: _FakeResp())
    return service


# -------------------------------------------------------------------------#
#                                 Tests                                    #
# -------------------------------------------------------------------------#
def test_insert_and_update(svc):
    """First sync inserts, second sync updates and resets stale."""

    # First run → INSERT
    res1 = svc.update_jupiter_positions()
    assert res1["imported"] == 1 and res1["updated"] == 0
    cur = svc.dl.db.get_cursor()
    cur.execute("SELECT stale FROM positions WHERE id='pos_1'")
    assert cur.fetchone()[0] == 0

    # Mark record stale manually
    cur.execute("UPDATE positions SET stale = 2 WHERE id='pos_1'")
    svc.dl.db.commit()

    # Second run → UPDATE → stale reset
    res2 = svc.update_jupiter_positions()
    assert res2["imported"] == 0 and res2["updated"] == 1
    cur.execute("SELECT stale FROM positions WHERE id='pos_1'")
    assert cur.fetchone()[0] == 0


def test_stale_handler_soft_close(svc):
    """After 3 consecutive misses position should be soft‑closed."""

    # Pre‑insert a position that will not re‑appear
    cur = svc.dl.db.get_cursor()
    cur.execute(
        "INSERT INTO positions (id, asset_type) VALUES ('pos_stale', 'BTC')"
    )
    svc.dl.db.commit()

    # Run stale handler 3 times (without pos_stale in live set)
    for _ in range(3):
        svc._handle_stale_positions(live_ids=set())

    cur.execute("SELECT status FROM positions WHERE id='pos_stale'")
    assert cur.fetchone()[0] == "STALE_CLOSED"

def test_heat_index_calculated_on_insert(svc):
    svc.update_jupiter_positions()
    cur = svc.dl.db.get_cursor()
    cur.execute("SELECT heat_index FROM positions WHERE id='pos_1'")
    value = cur.fetchone()[0]
    assert value is not None and value > 0


def test_upsert_triggers_hedge_update(monkeypatch):
    dl = _FakeDataLocker()
    svc = PositionSyncService(dl)

    cursor = svc.dl.db.get_cursor()
    cursor.execute("PRAGMA table_info(positions)")
    db_columns = {row[1] for row in cursor.fetchall()}

    called = {"update": False}
    monkeypatch.setattr(
        HedgeCore,
        "update_hedges",
        lambda self: called.__setitem__("update", True),
    )

    pos = {
        "id": "u1",
        "asset_type": "BTC",
        "position_type": "LONG",
        "entry_price": 1.0,
        "liquidation_price": 0.5,
        "collateral": 1.0,
        "size": 0.1,
        "leverage": 1.0,
        "value": 1.0,
        "last_updated": datetime.now().isoformat(),
        "wallet_name": "w",
        "pnl_after_fees_usd": 0.0,
        "travel_percent": 0.0,
        "current_price": 0.0,
        "heat_index": 0.0,
        "current_heat_index": 0.0,
        "liquidation_distance": 0.0,
    }

    inserted = svc._upsert_position(pos, db_columns)

    assert inserted is True
    assert called["update"] is True


def test_upsert_updates_wallet_balance(monkeypatch):
    dl = _FakeDataLocker()
    svc = PositionSyncService(dl)

    cursor = svc.dl.db.get_cursor()
    cursor.execute("PRAGMA table_info(positions)")
    db_columns = {row[1] for row in cursor.fetchall()}

    pos = {
        "id": "w1p1",
        "asset_type": "BTC",
        "position_type": "LONG",
        "entry_price": 1.0,
        "liquidation_price": 0.5,
        "collateral": 1.0,
        "size": 0.1,
        "leverage": 1.0,
        "value": 2.5,
        "last_updated": datetime.now().isoformat(),
        "wallet_name": "Wallet-A",
        "pnl_after_fees_usd": 0.0,
        "travel_percent": 0.0,
        "current_price": 0.0,
        "heat_index": 0.0,
        "current_heat_index": 0.0,
        "liquidation_distance": 0.0,
    }

    monkeypatch.setattr(
        TraderUpdateService,
        "refresh_trader_for_wallet",
        lambda self, wallet_name: dl.update_wallet(wallet_name, {"balance": pos["value"]}) or 1,
    )

    svc._upsert_position(pos, db_columns)
    assert dl.get_wallet_by_name("Wallet-A")["balance"] == 2.5


def test_wallet_noise_is_cleaned(monkeypatch):
    """Wallet strings with metadata should still hit Jupiter with base58."""

    target = "5Egu5iBD5TvXPR7i5QazQi6JT51LZrq8P3dYRcM3wHz6"
    dl = _FakeDataLocker()
    wallet = dl.read_wallets()[0]
    wallet["public_address"] = f"# GPT address={target} base58=7L2Q4bSmnShW9nykHLHJ4B3WmZ3G82UDeXwq5H8C7akB"

    svc = PositionSyncService(dl)

    captured_urls: list[str] = []

    class _FakeResp:
        status_code = 200

        def json(self):
            return {"dataList": []}

        text = "{}"

        def raise_for_status(self):
            pass

    def fake_request(url, *_a, **_k):
        captured_urls.append(url)
        return _FakeResp()

    monkeypatch.setattr(svc, "_request_with_retries", fake_request)

    signer_stub = SimpleNamespace(pubkey=lambda: target)

    import backend.core.positions_core.position_sync_service as backend_module

    monkeypatch.setattr(backend_module, "load_signer", lambda: signer_stub)

    try:
        import positions.position_sync_service as svc_module
    except ModuleNotFoundError:
        svc_module = None
    else:
        monkeypatch.setattr(svc_module, "load_signer", lambda: signer_stub)

    res = svc.update_jupiter_positions()

    assert res["errors"] == 0
    assert captured_urls, "expected Jupiter requests"
    assert f"walletAddress={target}" in captured_urls[0]
