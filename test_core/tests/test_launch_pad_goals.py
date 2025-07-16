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

    class DummySessionMgr:
        def get_active_session(self):
            called["view"] = True
            return launch_pad.Session(
                id="s1",
                session_start_value=0.0,
                current_session_value=0.0,
                session_goal_value=0.0,
            )

        def start_session(self, *a, **k):
            pass

        def update_session(self, *a, **k):
            pass

        def reset_session(self):
            pass

    class DummyLocker:
        def __init__(self, *a, **k):
            self.session = DummySessionMgr()

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
    return launch_pad.Session(
        id="s1",
        session_start_time=dt or datetime.utcnow(),
        session_start_value=0.0,
        current_session_value=0.0,
        session_goal_value=0.0,
        session_performance_value=0.0,
        status="OPEN",
        notes=None,
    )


def _setup_edit_menu(monkeypatch, start_input):
    updated = {}

    class DummySessionMgr:
        def __init__(self):
            self.active = _dummy_snapshot(datetime(2024, 1, 1, 12, 0, 0))

        def get_active_session(self):
            return self.active

        def start_session(self, *_a, **_k):
            return self.active

        def update_session(self, _id, fields):
            updated.update(fields)
            return self.active

        def reset_session(self):
            return self.active

    class DummyLocker:
        def __init__(self, *_a, **_k):
            self.session = DummySessionMgr()

    inputs = iter([
        "2",
        start_input,
        "",  # start value
        "",  # current value
        "",  # goal value
        "",  # perf value
        "",  # status
        "",  # notes
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
