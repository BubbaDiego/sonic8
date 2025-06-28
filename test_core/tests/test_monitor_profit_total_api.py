import importlib
import types

from tests.test_sonic_app_launch_route import _prepare_sonic_env


def _load_app(monkeypatch, positions):
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

    class DummyPositionCore:
        def __init__(self, _dl):
            self._positions = positions
        def get_active_positions(self):
            return list(self._positions)

    monkeypatch.setitem(sys.modules, 'positions.position_core', types.SimpleNamespace(PositionCore=DummyPositionCore))

    mod = importlib.reload(importlib.import_module('sonic_app'))
    mod.current_app.data_locker = mod.app.data_locker
    return mod


def test_profit_total_api(monkeypatch):
    app = _load_app(monkeypatch, [{'pnl_after_fees_usd': 10}, {'pnl_after_fees_usd': 5.5}])
    assert app.api_monitor_profit_total() == {'profit': '15.50'}


def test_profit_total_ignores_losses(monkeypatch):
    app = _load_app(
        monkeypatch,
        [
            {'pnl_after_fees_usd': 10},
            {'pnl_after_fees_usd': -5},
            {'pnl_after_fees_usd': 3.25},
        ],
    )
    assert app.api_monitor_profit_total() == {'profit': '13.25'}


def test_profit_total_api_empty(monkeypatch):
    app = _load_app(monkeypatch, [])
    assert app.api_monitor_profit_total() == {'profit': '0.00'}
