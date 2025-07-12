import types
import pytest
from backend.data.data_locker import DataLocker
from backend.core.trader_core.trader_core import TraderCore
from backend.core.positions_core.position_core import PositionCore


def _disable_seeding(monkeypatch):
    monkeypatch.setattr(DataLocker, "_seed_modifiers_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_wallets_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_thresholds_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alerts_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alert_config_if_empty", lambda self: None)


class DummyPersonaManager:
    def __init__(self, name="TestBot"):
        self.persona = types.SimpleNamespace(
            name=name,
            avatar="",
            profile=name,
            origin_story="",
            risk_profile="",
            moods={"stable": "neutral"},
            strategy_weights={},
        )

    def get(self, name):
        return self.persona

    def list_personas(self):
        return [self.persona.name]


class DummyStrategyManager:
    pass


@pytest.fixture
def dl(tmp_path, monkeypatch):
    _disable_seeding(monkeypatch)
    db_path = tmp_path / "trader_update.db"
    locker = DataLocker(str(db_path))
    # return plain dicts for position queries
    def _active(wallet_name):
        cur = locker.db.get_cursor()
        cur.execute(
            "SELECT * FROM positions WHERE wallet_name=? AND status='ACTIVE'",
            (wallet_name,),
        )
        return [dict(row) for row in cur.fetchall()]

    def _all():
        cur = locker.db.get_cursor()
        cur.execute("SELECT * FROM positions")
        return [dict(row) for row in cur.fetchall()]

    monkeypatch.setattr(locker.positions, "get_active_positions_by_wallet", _active)
    monkeypatch.setattr(locker.positions, "get_all_positions", _all)
    monkeypatch.setattr(
        DataLocker,
        "get_instance",
        classmethod(lambda cls, db_path=str(db_path): locker),
    )
    yield locker
    locker.db.close()


def _setup_trader(dl):
    wallet = "TestBotVault"
    dl.create_wallet({"name": wallet, "public_address": "x", "private_address": ""})
    dl.positions.create_position({
        "id": "p1",
        "wallet_name": wallet,
        "entry_price": 1,
        "current_price": 6,
        "value": 10,
        "collateral": 5,
        "size": 1,
        "heat_index": 20,
        "status": "ACTIVE",
    })
    dl.positions.create_position({
        "id": "p2",
        "wallet_name": wallet,
        "entry_price": 2,
        "current_price": 7,
        "value": 5,
        "collateral": 3,
        "size": 1,
        "heat_index": 40,
        "status": "ACTIVE",
    })
    core = TraderCore(dl, DummyPersonaManager(), DummyStrategyManager())
    trader = core.create_trader("TestBot")
    core.save_trader(trader)
    dl.traders.create_trader(trader)
    return wallet, core


def test_create_position_updates_trader(dl):
    wallet, core = _setup_trader(dl)

    pc = PositionCore(dl)
    initial = dl.traders.get_trader_by_name("TestBot")
    pc.create_position({
        "id": "p3",
        "wallet_name": wallet,
        "entry_price": 3,
        "current_price": 9,
        "value": 5,
        "collateral": 3,
        "size": 1,
        "heat_index": 60,
        "status": "ACTIVE",
    })

    trader = dl.traders.get_trader_by_name("TestBot")
    assert trader.wallet_balance == 20


def test_delete_position_updates_trader(dl):
    wallet, core = _setup_trader(dl)

    pc = PositionCore(dl)
    initial = dl.traders.get_trader_by_name("TestBot")
    pc.delete_position("p1")

    trader = dl.traders.get_trader_by_name("TestBot")
    assert trader.wallet_balance == 5
