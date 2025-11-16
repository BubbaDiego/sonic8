import types
from datetime import datetime, timedelta
from backend.utils.time_utils import PACIFIC_TZ
from flask import Flask, request, jsonify
import monitor.profit_monitor as pm
import monitor.risk_monitor as rm
from tests.conftest import flask_stub

if not hasattr(flask_stub.Flask, "route"):
    def _route(self, rule, methods=None):
        methods = methods or ["GET"]
        def decorator(func):
            for m in methods:
                self.routes.setdefault(rule, {})[m] = func
            return func
        return decorator
    flask_stub.Flask.route = _route


class DummySystem:
    def __init__(self):
        self.vars = {}

    def set_var(self, key, value):
        self.vars[key] = value

    def get_var(self, key):
        return self.vars.get(key)


class DummyLocker:
    def __init__(self, system=None):
        self.system = system or DummySystem()
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


class DummyProfitThresholdSvc:
    def __init__(self, _):
        pass

    def get_thresholds(self, alert_type, alert_class, condition):
        if alert_type == "TotalProfit":
            return types.SimpleNamespace(low=25, medium=50, high=75)
        if alert_type == "Profit":
            return types.SimpleNamespace(low=10, medium=20, high=25)
        return None


class DummyRiskThresholdSvc:
    def __init__(self, _):
        pass

    def get_thresholds(self, alert_type, alert_class, condition):
        if alert_type == "HeatIndex":
            return types.SimpleNamespace(low=40, medium=70, high=90)
        return None


def _setup_profit_monitor(monkeypatch, system, positions):
    monkeypatch.setattr(pm, "DataLocker", lambda *_a, **_k: DummyLocker(system))
    monkeypatch.setattr(pm, "PositionCore", lambda _dl: DummyPositionCore(_dl, positions))
    xc = DummyXComCore(None)
    monkeypatch.setattr(pm, "XComCore", lambda _sys: xc)
    monkeypatch.setattr(pm, "ThresholdService", DummyProfitThresholdSvc)
    monitor = pm.ProfitMonitor()
    monitor.xcom_core = xc
    return monitor, xc


def _setup_risk_monitor(monkeypatch, system, positions):
    monkeypatch.setattr(rm, "DataLocker", lambda *_a, **_k: DummyLocker(system))
    monkeypatch.setattr(rm, "PositionCore", lambda _dl: DummyPositionCore(_dl, positions))
    xc = DummyXComCore(None)
    monkeypatch.setattr(rm, "XComCore", lambda _sys: xc)
    monkeypatch.setattr(rm, "ThresholdService", DummyRiskThresholdSvc)
    monitor = rm.RiskMonitor()
    monitor.xcom_core = xc
    return monitor, xc


def _make_app(system):
    app = Flask(__name__)
    app.data_locker = DummyLocker(system)

    def api_snooze():
        data = request.get_json() or {}
        duration = int(data.get("duration", 300))
        until = datetime.now(PACIFIC_TZ) + timedelta(seconds=duration)
        app.data_locker.system.set_var("snooze_until", until.isoformat())
        return jsonify({"snooze_until": until.isoformat()})

    app.routes.setdefault("/api/monitor/snooze", {})["POST"] = api_snooze

    def api_snooze_increment():
        if request.method == "POST":
            data = request.get_json() or {}
            seconds = int(data.get("seconds", 60))
            app.data_locker.system.set_var("snooze_increment", seconds)
            return jsonify({"success": True, "seconds": seconds})
        value = app.data_locker.system.get_var("snooze_increment")
        return jsonify({"seconds": int(value) if value is not None else 60})

    app.routes.setdefault("/api/monitor/snooze_increment", {})["GET"] = api_snooze_increment
    app.routes["/api/monitor/snooze_increment"]["POST"] = api_snooze_increment

    def api_phone_relax():
        if request.method == "POST":
            data = request.get_json() or {}
            seconds = int(data.get("seconds", 0))
            app.data_locker.system.set_var("phone_relax_period", seconds)
            return jsonify({"success": True, "seconds": seconds})
        value = app.data_locker.system.get_var("phone_relax_period")
        return jsonify({"seconds": int(value) if value is not None else 0})

    app.routes.setdefault("/api/monitor/phone_relax", {})["GET"] = api_phone_relax
    app.routes["/api/monitor/phone_relax"]["POST"] = api_phone_relax

    def api_snooze_remaining():
        now = datetime.now(PACIFIC_TZ)
        snooze_until = app.data_locker.system.get_var("snooze_until")
        if snooze_until:
            try:
                snooze_until = datetime.fromisoformat(snooze_until)
            except Exception:
                snooze_until = None
        phone_relax = int(app.data_locker.system.get_var("phone_relax_period") or 0)
        last_call = app.data_locker.system.get_var("phone_last_call")
        phone_remaining = 0
        if last_call and phone_relax > 0:
            try:
                last_dt = datetime.fromisoformat(last_call)
                phone_until = last_dt + timedelta(seconds=phone_relax)
                if phone_until > now:
                    phone_remaining = (phone_until - now).total_seconds()
            except Exception:
                phone_remaining = 0
        snooze_remaining = 0
        if snooze_until and snooze_until > now:
            snooze_remaining = (snooze_until - now).total_seconds()
        remaining = max(snooze_remaining, phone_remaining)
        return jsonify({
            "remaining_seconds": int(remaining),
            "phone_remaining_seconds": int(phone_remaining)
        })

    app.routes.setdefault("/api/monitor/snooze/remaining", {})["GET"] = api_snooze_remaining

    return app


def test_api_snooze_blocks_profit_alert(monkeypatch):
    system = DummySystem()
    app = _make_app(system)
    with app.test_client() as client:
        resp = client.post("/api/monitor/snooze", json={"duration": 60})
        assert resp.status_code == 200

    monitor, xc = _setup_profit_monitor(monkeypatch, system, [{"pnl_after_fees_usd": 80}])
    result = monitor._do_work()
    assert result["alert_triggered"] is True
    assert xc.sent == []


def test_api_snooze_blocks_risk_alert(monkeypatch):
    system = DummySystem()
    app = _make_app(system)
    with app.test_client() as client:
        resp = client.post("/api/monitor/snooze", json={"duration": 60})
        assert resp.status_code == 200

    monitor, xc = _setup_risk_monitor(monkeypatch, system, [{"heat_index": 95}])
    result = monitor._do_work()
    assert result["alert_triggered"] is True
    assert xc.sent == []


def test_snooze_increment_get_and_set(monkeypatch):
    system = DummySystem()
    app = _make_app(system)
    with app.test_client() as client:
        resp = client.get("/api/monitor/snooze_increment")
        assert resp.status_code == 200
        assert resp.get_json()["seconds"] == 60

        resp = client.post("/api/monitor/snooze_increment", json={"seconds": 120})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

        resp = client.get("/api/monitor/snooze_increment")
        assert resp.get_json()["seconds"] == 120


def test_phone_relax_get_and_set(monkeypatch):
    system = DummySystem()
    app = _make_app(system)
    with app.test_client() as client:
        resp = client.get("/api/monitor/phone_relax")
        assert resp.status_code == 200
        assert resp.get_json()["seconds"] == 0

        resp = client.post("/api/monitor/phone_relax", json={"seconds": 120})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

        resp = client.get("/api/monitor/phone_relax")
        assert resp.get_json()["seconds"] == 120


def test_snooze_remaining_with_phone_delay(monkeypatch):
    system = DummySystem()
    app = _make_app(system)
    now = datetime.now(PACIFIC_TZ)
    system.set_var("phone_relax_period", 120)
    system.set_var("phone_last_call", now.isoformat())
    system.set_var("snooze_until", (now + timedelta(seconds=60)).isoformat())

    with app.test_client() as client:
        resp = client.get("/api/monitor/snooze/remaining")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["phone_remaining_seconds"] >= 119
        assert data["remaining_seconds"] >= data["phone_remaining_seconds"]
