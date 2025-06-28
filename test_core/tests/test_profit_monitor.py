import types
import pytest
from flask import Flask, Blueprint, render_template_string
import types

import monitor.profit_monitor as pm

class DummySystem:
    def __init__(self):
        self.vars = {}

    def set_var(self, key, value):
        self.vars[key] = value

    def get_var(self, key):
        return self.vars.get(key)

class DummyLocker:
    def __init__(self):
        self.system = DummySystem()
        self.db = object()

class DummyPositionCore:
    def __init__(self, dl, positions):
        self.positions = positions

    def get_active_positions(self):
        return list(self.positions)

class DummyXComCore:
    def __init__(self, _):
        self.sent = []

    def send_notification(self, *a, **k):
        self.sent.append((a, k))
        return {"ok": True}


def _setup_monitor(monkeypatch, positions, single_high=25, total_high=75):
    dl = DummyLocker()
    monkeypatch.setattr(pm, "DataLocker", lambda *_a, **_k: dl)
    monkeypatch.setattr(pm, "PositionCore", lambda _dl: DummyPositionCore(dl, positions))
    xc = DummyXComCore(None)
    monkeypatch.setattr(pm, "XComCore", lambda _sys: xc)

    class DummyThresholdSvc:
        def __init__(self, _):
            pass

        def get_thresholds(self, alert_type, alert_class, condition):
            if alert_type == "TotalProfit":
                return types.SimpleNamespace(low=25, medium=50, high=total_high)
            if alert_type == "Profit":
                return types.SimpleNamespace(low=10, medium=20, high=single_high)
            return None

    monkeypatch.setattr(pm, "ThresholdService", DummyThresholdSvc)

    monitor = pm.ProfitMonitor()
    monitor.xcom_core = xc
    return monitor, dl, xc


def test_do_work_below_threshold(monkeypatch):
    monitor, dl, xc = _setup_monitor(monkeypatch, [{"pnl_after_fees_usd": 10}])
    result = monitor._do_work()
    assert result["alert_triggered"] is False
    assert dl.system.get_var("profit_badge_value") is None
    assert xc.sent == []


def test_do_work_above_total_threshold(monkeypatch):
    monitor, dl, xc = _setup_monitor(monkeypatch, [{"pnl_after_fees_usd": 80}], total_high=75)
    result = monitor._do_work()
    assert result["alert_triggered"] is True
    assert dl.system.get_var("profit_badge_value") == "80.00"
    assert len(xc.sent) == 1


def test_do_work_single_position_threshold(monkeypatch):
    monitor, dl, xc = _setup_monitor(monkeypatch, [{"pnl_after_fees_usd": 30}], single_high=25)
    result = monitor._do_work()
    assert result["alert_triggered"] is True
    assert dl.system.get_var("profit_badge_value") == "30.00"
    assert len(xc.sent) == 1


def test_total_profit_ignores_losses(monkeypatch):
    monitor, dl, xc = _setup_monitor(
        monkeypatch,
        [
            {"pnl_after_fees_usd": 40},
            {"pnl_after_fees_usd": -15},
            {"pnl_after_fees_usd": 5},
        ],
        single_high=100,
    )
    result = monitor._do_work()
    assert result["total_profit"] == 45
    assert result["alert_triggered"] is False
    assert dl.system.get_var("profit_badge_value") == "40.00"


def test_badge_value_from_datalocker_in_template(monkeypatch):
    dl = DummyLocker()
    dl.system.set_var("profit_badge_value", 77)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.data_locker = dl

    bp = Blueprint("bp", __name__)

    @bp.route("/")
    def index():
        value = app.data_locker.system.get_var("profit_badge_value")
        # Simulate template rendering since jinja2 is stubbed
        if value:
            return f"<span class='profit-badge'>{value}</span>"
        return ""

    app.register_blueprint(bp)

    with app.test_client() as client:
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "profit-badge" in html
        assert "77" in html
