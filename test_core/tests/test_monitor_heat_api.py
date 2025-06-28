import importlib
import types

from tests.test_sonic_app_launch_route import _prepare_sonic_env


def _load_app(monkeypatch, value):
    _prepare_sonic_env(monkeypatch)
    import sys
    flask_mod = sys.modules['flask']
    # jsonify should return the given dict for assertions
    monkeypatch.setattr(flask_mod, 'jsonify', lambda obj=None, **k: obj if obj is not None else k)
    monkeypatch.setattr(flask_mod, 'request', object(), raising=False)
    class DummyBP:
        def __init__(self, *a, **k):
            pass
        def route(self, *a, **k):
            def decorator(f):
                return f
            return decorator
    monkeypatch.setattr(flask_mod, 'Blueprint', DummyBP, raising=False)
    monkeypatch.setattr(flask_mod, 'render_template', lambda *a, **k: "", raising=False)

    import dashboard.dashboard_service as ds
    monkeypatch.setattr(ds, 'get_heat_badge_value', lambda dl: value)

    mod = importlib.reload(importlib.import_module('sonic_app'))
    mod.current_app.data_locker = mod.app.data_locker
    return mod


def test_heat_api_valid_string(monkeypatch):
    app = _load_app(monkeypatch, "70")
    assert app.api_monitor_heat() == {"heat_percentage": "70"}


def test_heat_api_valid_number(monkeypatch):
    app = _load_app(monkeypatch, 55)
    assert app.api_monitor_heat() == {"heat_percentage": "55"}


def test_heat_api_invalid(monkeypatch):
    app = _load_app(monkeypatch, [1, 2])
    assert app.api_monitor_heat() == {"heat_percentage": "0"}
