import os
import time
import types
import pytest

from backend.data.data_locker import DataLocker


@pytest.fixture
def dl(tmp_path, monkeypatch):
    db_path = tmp_path / "ut.db"
    dl = DataLocker(str(db_path))
    # Ensure tests use our instance
    monkeypatch.setattr(DataLocker, "get_instance", classmethod(lambda cls: dl))
    # Create a minimal global_config surface the gates read
    dl.global_config = {
        "monitor": {"xcom_live": True},
        "channels": {"voice": {"enabled": True}},
    }
    return dl


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # keep Twilio paths inert by default
    for k in (
        "XCOM_LIVE",
        "XCOM_ACTIVE",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_FROM_PHONE",
        "TWILIO_PHONE_NUMBER",
        "TWILIO_TO_PHONE",
        "TWILIO_FLOW_SID",
        "TWILIO_COOLDOWN_SEC",
    ):
        monkeypatch.delenv(k, raising=False)
    yield


def set_future(dl, key, seconds):
    ts = time.time() + seconds
    dl.system.set_var(key, ts)
    return ts
