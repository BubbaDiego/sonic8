import os, time, pytest
from backend.data.data_locker import DataLocker

@pytest.fixture
def dl(tmp_path, monkeypatch):
    # Minimal DataLocker with its own temp DB
    db_path = tmp_path / "ut.db"
    dl = DataLocker(str(db_path))
    # Make get_instance() return this fixture instance
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    # Minimal config surface used by gates
    dl.global_config = {
        "monitor": {"xcom_live": True},
        "channels": {"voice": {"enabled": True}},
    }
    return dl

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # Keep Twilio/network inert for tests
    for k in (
        "XCOM_LIVE","XCOM_ACTIVE",
        "TWILIO_ACCOUNT_SID","TWILIO_AUTH_TOKEN",
        "TWILIO_FROM_PHONE","TWILIO_PHONE_NUMBER","MY_PHONE_NUMBER",
        "VOICE_COOLDOWN_SECONDS",
        "SONIC_MONITOR_INTERVAL","MONITOR_LOOP_SECONDS",
    ):
        monkeypatch.delenv(k, raising=False)
    yield

def set_future(dl, key, seconds):
    ts = time.time() + seconds
    dl.system.set_var(key, ts)
    return ts
