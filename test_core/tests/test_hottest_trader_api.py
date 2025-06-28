import importlib
import types

from tests.test_sonic_app_launch_route import _prepare_sonic_env


def _load_app(monkeypatch, info):
    _prepare_sonic_env(monkeypatch)
    import sys
    flask_mod = sys.modules['flask']
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
    monkeypatch.setattr(ds, 'get_hottest_trader_info', lambda dl: info)

    mod = importlib.reload(importlib.import_module('sonic_app'))
    mod.current_app.data_locker = mod.app.data_locker
    return mod


def test_hottest_trader_api(monkeypatch):
    info = {'trader': 'Chewie', 'heat_index': 75.5, 'icon': '/static/chewie.jpg'}
    app = _load_app(monkeypatch, info)
    assert app.api_monitor_hottest_trader() == info


def test_hottest_trader_api_default(monkeypatch):
    app = _load_app(monkeypatch, {'trader': '', 'heat_index': 0, 'icon': ''})
    assert app.api_monitor_hottest_trader() == {'trader': '', 'heat_index': 0, 'icon': ''}
