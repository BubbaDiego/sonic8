
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


def test_build_hedges_accepts_mixed_input(hedge_core):
    pos_dict = {
        "id": "long1",
        "wallet_name": "walletA",
        "asset_type": "BTC",
        "position_type": "LONG",
        "size": 1.0,
        "heat_index": 1.0,
        "hedge_buddy_id": "h1",
    }
    pos_obj = PositionDB(
        id="short1",
        wallet_name="walletA",
        asset_type="BTC",
        position_type="SHORT",
        size=1.0,
        heat_index=1.0,
        hedge_buddy_id="h1",
    )

    hedges = hedge_core.build_hedges([pos_dict, pos_obj])

    assert len(hedges) == 1
    hedge = hedges[0]
    assert hedge.id == "h1"
    assert set(hedge.positions) == {"long1", "short1"}


def test_link_hedges_handles_mixed_records(hedge_core, monkeypatch):
    long_pos = PositionDB(id="long1", wallet_name="walletA", asset_type="BTC", position_type="LONG")
    short_pos = PositionDB(id="short1", wallet_name="walletA", asset_type="BTC", position_type="SHORT")

    hedge_core.dl.positions.create_position(long_pos)
    hedge_core.dl.positions.create_position(short_pos)

    mixed = [long_pos.model_dump(), short_pos]
    monkeypatch.setattr(hedge_core.dl.positions, "get_all_positions", lambda: mixed)

    hedged_groups = hedge_core.link_hedges()

    assert len(hedged_groups) == 1
    hedge_ids = []
    for rec in mixed:
        hedge_ids.append(rec["hedge_buddy_id"] if isinstance(rec, dict) else getattr(rec, "hedge_buddy_id", None))

    assert len({hid for hid in hedge_ids if hid}) == 1
