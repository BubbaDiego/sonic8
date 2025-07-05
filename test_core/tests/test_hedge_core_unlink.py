
import pytest
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.core.hedge_core.hedge_core import HedgeCore
from data.data_locker import DataLocker
from backend.models.position import PositionDB

@pytest.fixture
def hedge_core():
    dl = DataLocker(':memory:')
    dl.initialize_database()
    return HedgeCore(dl)

def test_unlink_hedges_clears_ids(hedge_core):
    hedge_id = "existing-hedge-uuid"
    positions = [
        PositionDB(id="long1", wallet_name="walletA", asset_type="BTC", position_type="LONG", hedge_buddy_id=hedge_id),
        PositionDB(id="short1", wallet_name="walletA", asset_type="BTC", position_type="SHORT", hedge_buddy_id=hedge_id)
    ]

    for pos in positions:
        hedge_core.dl.positions.create_position(pos)

    hedge_core.unlink_hedges()

    positions = hedge_core.dl.positions.get_all_positions()
    hedge_ids = {pos.hedge_buddy_id for pos in positions}
    assert hedge_ids == {None}
