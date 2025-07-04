import asyncio
import sys
import types

import pytest

from cyclone.cyclone_engine import Cyclone
from cyclone import cyclone_engine
from positions.position_core_service import PositionCoreService
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
        self.alert_list = []
        class DummySystem:
            def get_var(self, _):
                return {}
            def set_var(self, key, value):
                pass
        self.system = DummySystem()
    def get_alerts(self):
        return self.alert_list

@pytest.mark.asyncio
async def test_prune_stale_positions(monkeypatch):
    dl = MockDataLocker()
    dl.positions.create_position({"id": "pos1", "stale": 2})
    dl.positions.create_position({"id": "pos2", "stale": 1})
    dl.alert_list = [
        {"id": "a1", "position_reference_id": "pos1"},
        {"id": "a2", "position_reference_id": "pos2"},
    ]

    monkeypatch.setattr(cyclone_engine, "global_data_locker", dl)

    deleted = []
    def fake_delete(self, pid):
        deleted.append(pid)
        dl.positions.delete_position(pid)
        dl.alert_list[:] = [a for a in dl.alert_list if a.get("position_reference_id") != pid]
    monkeypatch.setattr(PositionCoreService, "delete_position_and_cleanup", fake_delete)

    cyc = Cyclone()
    await cyc.run_prune_stale_positions()

    assert deleted == ["pos1"]
    remaining = dl.positions.get_all_positions()
    assert len(remaining) == 1 and remaining[0]["id"] == "pos2"
    assert dl.alert_list == [{"id": "a2", "position_reference_id": "pos2"}]


@pytest.mark.asyncio
async def test_prune_stale_positions_base_model(monkeypatch):
    dl = MockDataLocker()
    dl.positions.create_position(PositionDB(id="pos1", stale=2))
    dl.positions.create_position(PositionDB(id="pos2", stale=1))
    dl.alert_list = [
        {"id": "a1", "position_reference_id": "pos1"},
        {"id": "a2", "position_reference_id": "pos2"},
    ]

    monkeypatch.setattr(cyclone_engine, "global_data_locker", dl)

    deleted = []

    def fake_delete(self, pid):
        deleted.append(pid)
        dl.positions.delete_position(pid)
        dl.alert_list[:] = [a for a in dl.alert_list if a.get("position_reference_id") != pid]

    monkeypatch.setattr(PositionCoreService, "delete_position_and_cleanup", fake_delete)

    cyc = Cyclone()
    await cyc.run_prune_stale_positions()

    assert deleted == ["pos1"]
    remaining = dl.positions.get_all_positions()
    assert len(remaining) == 1 and getattr(remaining[0], "id", remaining[0]["id"]) == "pos2"
    assert dl.alert_list == [{"id": "a2", "position_reference_id": "pos2"}]
