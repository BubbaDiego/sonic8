import pytest
from backend.data.data_locker import DataLocker
from backend.core.positions_core.position_core import PositionCore
from backend.core.positions_core.position_core_service import PositionCoreService
from backend.core.positions_core.position_sync_service import PositionSyncService
from backend.models.position import PositionDB


def _setup(dl):
    dl.create_wallet({"name": "W1", "public_address": "a"})
    dl.create_wallet({"name": "W2", "public_address": "b"})

    core = PositionCore(dl)
    core.create_position(PositionDB(id="p1", asset_type="BTC", position_type="long", entry_price=1, size=1, leverage=1, wallet_name="W1", value=100))
    core.create_position(PositionDB(id="p2", asset_type="BTC", position_type="long", entry_price=1, size=4, leverage=1, wallet_name="W1", value=400))
    core.create_position(PositionDB(id="p3", asset_type="ETH", position_type="long", entry_price=1, size=2, leverage=1, wallet_name="W2", value=200))


def test_balance_after_delete(dl_tmp):
    _setup(dl_tmp)
    core = PositionCore(dl_tmp)
    assert dl_tmp.get_wallet_by_name("W1")["balance"] == 500
    core.delete_position("p1")
    assert dl_tmp.get_wallet_by_name("W1")["balance"] == 400


def test_balance_after_stale_close(dl_tmp):
    _setup(dl_tmp)
    # Manually insert a near-stale position without refresh
    dl_tmp.positions.create_position({
        "id": "p4", "asset_type": "BTC", "position_type": "long",
        "entry_price": 1, "size": 1, "leverage": 1, "wallet_name": "W1",
        "value": 100, "stale": 2
    })
    PositionCore.reconcile_wallet_balances(dl_tmp)
    assert dl_tmp.get_wallet_by_name("W1")["balance"] == 600

    svc = PositionSyncService(dl_tmp)
    svc._handle_stale_positions(set())  # marks p4 stale->closed
    assert dl_tmp.get_wallet_by_name("W1")["balance"] == 500
