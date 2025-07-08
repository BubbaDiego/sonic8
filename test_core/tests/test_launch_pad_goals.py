import builtins
import sys
import types

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
