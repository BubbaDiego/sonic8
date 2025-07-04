import os
import core.constants as const
import core.core_imports as ci
from data.data_locker import DataLocker
from backend.core.positions_core.position_core import PositionCore
from backend.core.calc_core.calc_services import CalcServices
from backend.models.portfolio import PortfolioSnapshot

SEED_PATCHES = [
    "_seed_modifiers_if_empty",
    "_seed_wallets_if_empty",
    "_seed_thresholds_if_empty",
    "_seed_alerts_if_empty",
]

def setup_db(tmp_path, monkeypatch):
    db_path = tmp_path / "inactive.db"
    os.environ["MOTHER_DB_PATH"] = str(db_path)
    const.MOTHER_DB_PATH = db_path
    const.DB_PATH = db_path
    ci.MOTHER_DB_PATH = db_path
    ci.DB_PATH = db_path
    for name in SEED_PATCHES:
        monkeypatch.setattr(DataLocker, name, lambda self: None)
    return db_path


def init_locker(db_path):
    return DataLocker.get_instance(str(db_path))


def test_inactive_wallet_positions_excluded(tmp_path, monkeypatch):
    db = setup_db(tmp_path, monkeypatch)
    dl = init_locker(db)
    dl.create_wallet({"name": "active", "public_address": "a", "is_active": True})
    dl.create_wallet({"name": "inactive", "public_address": "b", "is_active": False})

    dl.positions.create_position({"id": "p1", "wallet_name": "active", "value": 5, "status": "ACTIVE"})
    dl.positions.create_position({"id": "p2", "wallet_name": "inactive", "value": 7, "status": "ACTIVE"})

    core = PositionCore(dl)
    positions = core.get_active_positions()
    names = {p.get("wallet_name") for p in positions}
    assert "active" in names
    assert "inactive" not in names

    core.record_snapshot()
    snap = dl.portfolio.get_latest_snapshot()
    assert isinstance(snap, PortfolioSnapshot)
    assert snap.total_value == 5


