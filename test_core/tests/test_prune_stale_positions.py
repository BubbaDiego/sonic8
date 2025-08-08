import pytest

from backend.core.cyclone_core.cyclone_engine import Cyclone
from backend.core.cyclone_core import cyclone_engine
from backend.core.positions_core.position_core_service import PositionCoreService
from backend.models.position import PositionDB

class DummyDB:
    def __init__(self):
        self.positions = {}
    def get_cursor(self):
        return self
    def execute(self, *a, **k):
        return self
    def commit(self):
        pass
    def close(self):
        pass

class DummyPositions:
    def __init__(self, db):
        self.db = db
    def create_position(self, pos):
        pos_id = getattr(pos, "id", None)
        if pos_id is None and isinstance(pos, dict):
            pos_id = pos["id"]
        self.db.positions[pos_id] = pos
    def get_all_positions(self):
        return list(self.db.positions.values())
    def delete_position(self, pid):
        self.db.positions.pop(pid, None)

class MockDataLocker:
    def __init__(self):
        self.db = DummyDB()
        self.positions = DummyPositions(self.db)
        class DummySystem:
            def get_var(self, _):
                return {}
            def set_var(self, key, value):
                pass
        self.system = DummySystem()

@pytest.mark.asyncio
async def test_prune_stale_positions(monkeypatch):
    dl = MockDataLocker()
    dl.positions.create_position({"id": "pos1", "stale": 2})
    dl.positions.create_position({"id": "pos2", "stale": 1})

    monkeypatch.setattr(cyclone_engine, "global_data_locker", dl)

    deleted = []
    def fake_delete(self, pid):
        deleted.append(pid)
        dl.positions.delete_position(pid)
    monkeypatch.setattr(PositionCoreService, "delete_position_and_cleanup", fake_delete)

    cyc = Cyclone()
    await cyc.run_prune_stale_positions()

    assert deleted == ["pos1"]
    remaining = dl.positions.get_all_positions()
    assert len(remaining) == 1 and remaining[0]["id"] == "pos2"


@pytest.mark.asyncio
async def test_prune_stale_positions_base_model(monkeypatch):
    dl = MockDataLocker()
    dl.positions.create_position(PositionDB(id="pos1", stale=2))
    dl.positions.create_position(PositionDB(id="pos2", stale=1))

    monkeypatch.setattr(cyclone_engine, "global_data_locker", dl)

    deleted = []

    def fake_delete(self, pid):
        deleted.append(pid)
        dl.positions.delete_position(pid)

    monkeypatch.setattr(PositionCoreService, "delete_position_and_cleanup", fake_delete)

    cyc = Cyclone()
    await cyc.run_prune_stale_positions()

    assert deleted == ["pos1"]
    remaining = dl.positions.get_all_positions()
    rem = remaining[0]
    rem_id = getattr(rem, "id", None)
    if rem_id is None and isinstance(rem, dict):
        rem_id = rem.get("id")
    assert len(remaining) == 1 and rem_id == "pos2"
