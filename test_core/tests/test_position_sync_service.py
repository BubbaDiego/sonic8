
from datetime import datetime
import sqlite3
from types import SimpleNamespace
import json
import pytest

from positions.position_sync_service import PositionSyncService


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
        super().__init__(
            db=db,
            positions=_FakePositionsFacade(db),
            read_wallets=lambda: [
                {"is_active": True, "public_address": "WALLET_A", "name": "Wallet‑A"}
            ],
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
