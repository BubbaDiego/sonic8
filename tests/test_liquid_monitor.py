import types
import sys

sys.modules.setdefault("requests", types.ModuleType("requests"))
sys.modules.setdefault("twilio", types.ModuleType("twilio"))
twilio_rest = types.ModuleType("twilio.rest")
twilio_rest.Client = object
sys.modules.setdefault("twilio.rest", twilio_rest)
twilio_twiml = types.ModuleType("twilio.twiml")
voice_module = types.ModuleType("twilio.twiml.voice_response")
voice_module.VoiceResponse = object
sys.modules.setdefault("twilio.twiml", twilio_twiml)
sys.modules.setdefault("twilio.twiml.voice_response", voice_module)

from backend.core.monitor_core import liquidation_monitor


class FakeConfig:
    def __init__(self, sections=None):
        self.sections = sections or {}

    def get_section(self, key):
        return self.sections.get(key)


class FakeDataLocker:
    def __init__(self, sections=None):
        self.config = FakeConfig(sections or {})
        # Minimal stand-ins for system vars and database manager
        self.system = types.SimpleNamespace(
            get_var=lambda key: self.config.get_section(key),
            set_var=lambda key, val: None,
        )
        self.db = object()

    def close(self):
        pass


class FakePositionManager:
    def __init__(self, positions):
        self._positions = positions

    def get_active_positions(self):
        return self._positions


class FakeXComCore:
    def __init__(self, dl):
        self.sent = []

    def send_notification(self, level, subject, body, initiator="system"):
        self.sent.append({
            "level": level,
            "subject": subject,
            "body": body,
            "initiator": initiator,
        })
        return True


def _make_position(dist):
    return types.SimpleNamespace(
        liquidation_distance=dist,
        asset_type="BTC",
        position_type="LONG",
        current_price=100.0,
        liquidation_price=95.0,
    )


def test_liquid_monitor_alert_and_snooze(monkeypatch):
    cfg = {
        "liquid_monitor": {
            "threshold_percent": 5.0,
            "snooze_seconds": 60,
            "windows_alert": False,
            "voice_alert": True,
            "level": "HIGH",
        }
    }
    dl = FakeDataLocker(cfg)
    monkeypatch.setattr(liquidation_monitor.DataLocker, "get_instance", classmethod(lambda cls: dl))
    fake_pm = FakePositionManager([_make_position(4.0)])
    called = {}

    def pm_factory(arg):
        called["db"] = arg
        return fake_pm

    monkeypatch.setattr(liquidation_monitor, "DLPositionManager", pm_factory)
    fake_xcom = FakeXComCore(dl)
    monkeypatch.setattr(liquidation_monitor, "XComCore", lambda _dl: fake_xcom)

    monitor = liquidation_monitor.LiquidationMonitor()
    assert called["db"] is dl.db

    first = monitor._do_work()
    assert first["alert_sent"] is True
    assert fake_xcom.sent

    second = monitor._do_work()
    assert second["alert_sent"] is False
    assert len(fake_xcom.sent) == 1
