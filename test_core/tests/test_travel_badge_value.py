import types

import dashboard.dashboard_service as ds

class DummySystem:
    def __init__(self, value=None):
        self.value = value
    def get_var(self, key):
        assert key == "travel_risk_badge_value"
        return self.value

class DummyLocker:
    def __init__(self, value=None, positions=None):
        self.system = DummySystem(value)
        self._positions = positions or []


def test_travel_badge_ignores_stored_value(monkeypatch):
    positions = [
        {"travel_percent": -20.0},
        {"travel_percent": -45.0},
        {"travel_percent": -10.0},
    ]
    dl = DummyLocker("55", positions)
    monkeypatch.setattr(
        ds,
        "PositionCore",
        lambda _dl: types.SimpleNamespace(get_active_positions=lambda: positions),
    )
    assert ds.get_travel_badge_value(dl) == "-45"


def test_travel_badge_computed_when_missing(monkeypatch):
    positions = [
        {"travel_percent": -20.0},
        {"travel_percent": -45.0},
        {"travel_percent": -10.0},
    ]
    dl = DummyLocker(None, positions)
    monkeypatch.setattr(
        ds,
        "PositionCore",
        lambda _dl: types.SimpleNamespace(get_active_positions=lambda: positions),
    )
    assert ds.get_travel_badge_value(dl) == "-45"
