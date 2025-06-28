# tests/positions/test_crud.py
from uuid import uuid4
from cores.positions_core.position_core import PositionCore

def test_insert_and_fetch(dl_tmp):
    core = PositionCore(dl_tmp)
    pid = str(uuid4())
    core.create_position({
        "id": pid,
        "asset_type": "BTC",
        "position_type": "long",
        "entry_price": 100,
        "size": 0.1,
        "leverage": 2,
        "wallet_name": "Test"
    })
    results = core.get_all_positions()
    ids = {p["id"] for p in results}
    assert pid in ids
