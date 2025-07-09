import builtins
import sys
import types
from datetime import datetime

import pytest

import tests.conftest  # noqa: F401

core_logging_stub = types.ModuleType("core.logging")

class _DummyLog:
    logger = types.SimpleNamespace(setLevel=lambda *a, **k: None)

    def __getattr__(self, _):
        def noop(*a, **k):
            pass
        return noop

core_logging_stub.log = _DummyLog()
core_logging_stub.configure_console_log = lambda *a, **k: None
sys.modules.setdefault("core.logging", core_logging_stub)

pyfiglet_stub = types.ModuleType("pyfiglet")
pyfiglet_stub.Figlet = object
sys.modules.setdefault("pyfiglet", pyfiglet_stub)

try:
    import launch_pad
except Exception:
    pytest.skip("launch_pad module unavailable", allow_module_level=True)


def test_goals_menu_view(monkeypatch):
    called = {"view": False}

    class DummyPortfolio:
        def get_latest_snapshot(self):
            called["view"] = True
            return launch_pad.PortfolioSnapshot(
                total_size=0.0,
                total_long_size=0.0,
                total_short_size=0.0,
                total_value=0.0,
                total_collateral=0.0,
                avg_leverage=0.0,
                avg_travel_percent=0.0,
                avg_heat_index=0.0,
            )

        def record_snapshot(self, *a, **k):
            pass

        def update_entry(self, *a, **k):
            pass

    class DummyLocker:
        def __init__(self, *a, **k):
            self.portfolio = DummyPortfolio()

    inputs = iter(["1", "", "0"])
    monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
    monkeypatch.setattr(launch_pad, "clear_screen", lambda: None)
    monkeypatch.setattr(launch_pad, "banner", lambda: None)
    monkeypatch.setattr(
        launch_pad.DataLocker,
        "get_instance",
        classmethod(lambda cls: DummyLocker()),
    )

    launch_pad.goals_menu()

    assert called["view"] is True


def _dummy_snapshot(dt=None):
    return launch_pad.PortfolioSnapshot(
        total_size=0.0,
        total_long_size=0.0,
        total_short_size=0.0,
        total_value=0.0,
        total_collateral=0.0,
        avg_leverage=0.0,
        avg_travel_percent=0.0,
        avg_heat_index=0.0,
        session_start_time=dt,
    )


def _setup_edit_menu(monkeypatch, start_input):
    updated = {}

    class DummyPortfolio:
        def __init__(self):
            self.latest = _dummy_snapshot(datetime(2024, 1, 1, 12, 0, 0))

        def get_latest_snapshot(self):
            return self.latest

        def record_snapshot(self, *_a, **_k):
            pass

        def update_entry(self, _id, fields):
            updated.update(fields)

    class DummyLocker:
        def __init__(self, *_a, **_k):
            self.portfolio = DummyPortfolio()

    inputs = iter([
        "2",
        start_input,
        "",
        "",
        "",
        "",
        "0",
    ])
    monkeypatch.setattr(builtins, "input", lambda _: next(inputs))
    monkeypatch.setattr(launch_pad, "clear_screen", lambda: None)
    monkeypatch.setattr(launch_pad, "banner", lambda: None)
    monkeypatch.setattr(
        launch_pad.DataLocker,
        "get_instance",
        classmethod(lambda cls: DummyLocker()),
    )
    return updated


def test_goals_menu_edit_invalid_time(monkeypatch):
    updated = _setup_edit_menu(monkeypatch, "bogus")
    launch_pad.goals_menu()
    assert updated["session_start_time"] == "2024-01-01T12:00:00"


def test_goals_menu_edit_valid_time(monkeypatch):
    updated = _setup_edit_menu(monkeypatch, "2024-05-06T08:30:00")
    launch_pad.goals_menu()
    assert updated["session_start_time"] == "2024-05-06T08:30:00"
