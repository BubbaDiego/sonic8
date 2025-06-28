import os
from xcom.xcom_config_service import XComConfigService

class DummySystem:
    def __init__(self):
        self.store = {}
    def get_var(self, key):
        return self.store.get(key)
    def set_var(self, key, value):
        self.store[key] = value


def test_get_provider_alias(monkeypatch):
    # Ensure environment variables do not interfere
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FLOW_SID", raising=False)
    monkeypatch.delenv("MY_PHONE_NUMBER", raising=False)
    monkeypatch.delenv("TWILIO_PHONE_NUMBER", raising=False)

    cfg = {
        "enabled": True,
        "account_sid": "sid",
        "auth_token": "token",
        "flow_sid": "flow",
        "default_to_phone": "+10000000000",
        "default_from_phone": "+19999999999",
    }
    sys = DummySystem()
    sys.set_var("xcom_providers", {"twilio": cfg})
    svc = XComConfigService(sys)

    provider = svc.get_provider("api")
    assert provider == cfg
