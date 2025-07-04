# tests/positions/test_crud.py
from uuid import uuid4
from core.positions_core.position_core import PositionCore
from backend.models.position import PositionDB

def test_insert_and_fetch(dl_tmp):
    core = PositionCore(dl_tmp)
    pid = str(uuid4())
    pos = PositionDB(
        id=pid,
        asset_type="BTC",
        position_type="long",
        entry_price=100,
        size=0.1,
        leverage=2,
        wallet_name="Test",
    )
    core.create_position(pos)
    results = core.get_all_positions()
    ids = {p.id for p in results}
    assert pid in ids
