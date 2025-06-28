import types
import monitor.profit_monitor as pm
from datetime import datetime

class DummySystem:
    def __init__(self):
        self.vars = {}

    def set_var(self, key, value):
        print(f"set_var {key}={value}")
        self.vars[key] = value

    def get_var(self, key):
        val = self.vars.get(key)
        print(f"get_var {key} -> {val}")
        return val

class DummyLocker:
    def __init__(self):
        self.system = DummySystem()
        self.db = object()

class DummyPositionCore:
    def __init__(self, dl, positions):
        self.positions = positions

    def get_active_positions(self):
        print("returning positions", self.positions)
        return list(self.positions)

class DummyXComCore:
    def __init__(self, _):
        self.sent = []

    def send_notification(self, *a, **k):
        print("xcom.send_notification", a, k)
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


def test_profit_monitor_logging(monkeypatch):
    monitor, dl, xc = _setup_monitor(monkeypatch, [{"pnl_after_fees_usd": 80}], total_high=75)
    result = monitor._do_work()
    print("result", result)
    print("system vars", dl.system.vars)
    print("xcom log", xc.sent)
