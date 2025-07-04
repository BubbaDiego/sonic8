
import pytest
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from hedge_core.hedge_core import HedgeCore
from data.data_locker import DataLocker
from backend.models.position import PositionDB

@pytest.fixture
def hedge_core():
    dl = DataLocker(':memory:')
    dl.initialize_database()
    return HedgeCore(dl)

def test_link_hedges_assigns_same_id_for_long_and_short(hedge_core):
    long_position = PositionDB(id="long1", wallet_name="walletA", asset_type="BTC", position_type="LONG")
    short_position = PositionDB(id="short1", wallet_name="walletA", asset_type="BTC", position_type="SHORT")
    hedge_core.dl.positions.create_position(long_position)
    hedge_core.dl.positions.create_position(short_position)

    hedge_core.link_hedges()

    positions = hedge_core.dl.positions.get_all_positions()
    hedge_ids = {pos.hedge_buddy_id for pos in positions}
    assert len(hedge_ids) == 1
    assert None not in hedge_ids

def test_link_hedges_preserves_existing_ids(hedge_core):
    existing_id = "existing-hedge-uuid"
    long_position = PositionDB(id="long1", wallet_name="walletA", asset_type="BTC", position_type="LONG", hedge_buddy_id=existing_id)
    short_position = PositionDB(id="short1", wallet_name="walletA", asset_type="BTC", position_type="SHORT")
    hedge_core.dl.positions.create_position(long_position)
    hedge_core.dl.positions.create_position(short_position)

    hedge_core.link_hedges()

    positions = hedge_core.dl.positions.get_all_positions()
    hedge_ids = {pos.hedge_buddy_id for pos in positions}
    assert hedge_ids == {existing_id}
