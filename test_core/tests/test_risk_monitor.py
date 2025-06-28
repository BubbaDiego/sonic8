import types
from flask import Flask, Blueprint

import monitor.risk_monitor as rm

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


def _setup_monitor(monkeypatch, positions, low=40, high=90, travel_low=50, travel_high=90):
    dl = DummyLocker()
    monkeypatch.setattr(rm, "DataLocker", lambda *_a, **_k: dl)
    monkeypatch.setattr(rm, "PositionCore", lambda _dl: DummyPositionCore(dl, positions))
    xc = DummyXComCore(None)
    monkeypatch.setattr(rm, "XComCore", lambda _sys: xc)

    class DummyThresholdSvc:
        def __init__(self, _):
            pass

        def get_thresholds(self, alert_type, alert_class, condition):
            if alert_type == "HeatIndex":
                return types.SimpleNamespace(low=low, medium=70, high=high)
            if alert_type == "TravelPercent":
                return types.SimpleNamespace(low=travel_low, medium=70, high=travel_high)
            return None

    monkeypatch.setattr(rm, "ThresholdService", DummyThresholdSvc)

    monitor = rm.RiskMonitor()
    monitor.xcom_core = xc
    return monitor, dl, xc


def test_no_alert_below_threshold(monkeypatch):
    monitor, dl, xc = _setup_monitor(monkeypatch, [{"heat_index": 20}])
    result = monitor._do_work()
    assert result["alert_triggered"] is False
    assert dl.system.get_var("risk_badge_value") is None
    assert xc.sent == []


def test_badge_without_alert(monkeypatch):
    monitor, dl, xc = _setup_monitor(monkeypatch, [{"heat_index": 50}], low=40, high=90)
    result = monitor._do_work()
    assert result["alert_triggered"] is False
    assert dl.system.get_var("risk_badge_value") == "50"
    assert xc.sent == []


def test_alert_and_badge(monkeypatch):
    monitor, dl, xc = _setup_monitor(monkeypatch, [{"heat_index": 95}], low=40, high=90)
    result = monitor._do_work()
    assert result["alert_triggered"] is True
    assert dl.system.get_var("risk_badge_value") == "95"
    assert len(xc.sent) == 1


def test_travel_percent_badge(monkeypatch):
    monitor, dl, xc = _setup_monitor(
        monkeypatch,
        [{"travel_percent": -60.0}],
        travel_low=50,
        travel_high=80,
    )
    result = monitor._do_work()
    assert result["alert_triggered"] is False
    assert dl.system.get_var("travel_risk_badge_value") == "-60"
    assert xc.sent == []


def test_travel_percent_alert(monkeypatch):
    monitor, dl, xc = _setup_monitor(
        monkeypatch,
        [{"travel_percent": -90.0}],
        travel_low=50,
        travel_high=80,
    )
    result = monitor._do_work()
    assert result["alert_triggered"] is True
    assert dl.system.get_var("travel_risk_badge_value") == "-90"
    assert len(xc.sent) == 1


def test_badge_template_render(monkeypatch):
    dl = DummyLocker()
    dl.system.set_var("risk_badge_value", 77)
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.data_locker = dl

    bp = Blueprint("bp", __name__)

    @bp.route("/")
    def index():
        value = app.data_locker.system.get_var("risk_badge_value")
        if value:
            return f"<span class='risk-badge'>{value}</span>"
        return ""

    app.register_blueprint(bp)

    with app.test_client() as client:
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode()
        assert "risk-badge" in html
        assert "77" in html

