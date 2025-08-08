from backend.core.positions_core.position_core_service import PositionCoreService


class DummyDB:
    def __init__(self):
        self.positions = {}

    def get_cursor(self):
        return self

    def execute(self, sql, params=()):
        if sql.startswith("UPDATE positions SET hedge_buddy_id = NULL"):
            target = params[0]
            for p in self.positions.values():
                if p.get("hedge_buddy_id") == target:
                    p["hedge_buddy_id"] = None
        return self

    def commit(self):
        pass

    def close(self):
        pass


class DummyPositions:
    def __init__(self, db: DummyDB):
        self.db = db
        self.deleted = []

    def create_position(self, pos):
        self.db.positions[pos["id"]] = pos

    def get_all_positions(self):
        return list(self.db.positions.values())

    def delete_position(self, pos_id):
        self.deleted.append(pos_id)
        self.db.positions.pop(pos_id, None)

    def get_position_by_id(self, pos_id):
        return self.db.positions.get(pos_id)


class MockDataLocker:
    def __init__(self):
        self.db = DummyDB()
        self.positions = DummyPositions(self.db)


def test_update_position_and_alert():
    dl = MockDataLocker()

    service = PositionCoreService(dl)
    pos = {"id": "pos1", "asset_type": "BTC", "position_type": "LONG"}

    service.update_position_and_alert(pos)

    stored = dl.positions.get_all_positions()
    assert len(stored) == 1
    assert stored[0]["id"] == "pos1"


def test_delete_position_and_cleanup():
    dl = MockDataLocker()

    # existing positions
    dl.positions.create_position({"id": "pos1", "asset_type": "BTC", "position_type": "LONG"})
    dl.positions.create_position({"id": "pos2", "asset_type": "BTC", "position_type": "SHORT", "hedge_buddy_id": "pos1"})

    service = PositionCoreService(dl)

    service.delete_position_and_cleanup("pos1")

    assert dl.positions.deleted == ["pos1"]

    remaining = dl.positions.get_all_positions()
    assert len(remaining) == 1
    assert remaining[0]["id"] == "pos2"
    assert remaining[0].get("hedge_buddy_id") is None
