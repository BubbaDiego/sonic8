import time
import pytest

from backend.data.data_locker import DataLocker
from backend.core.reporting_core.sonic_reporting.xcom_extras import (
    xcom_live_status,
    xcom_ready,
    xcom_guard,
    get_sonic_interval,
    read_snooze_remaining,
    read_voice_cooldown_remaining,
    set_voice_cooldown,
    get_default_voice_cooldown,
)


def test_live_status_file_wins_over_env(dl, monkeypatch):
    # FILE says ON
    dl.global_config["monitor"]["xcom_live"] = True
    # ENV tries to force OFF, but FILE should win in our probe order
    monkeypatch.setenv("XCOM_LIVE", "0")
    live, src = xcom_live_status(dl, dl.global_config)
    assert live is True and src == "FILE"


def test_live_status_env_used_when_no_file(dl, monkeypatch):
    dl.global_config.clear()
    monkeypatch.setenv("XCOM_LIVE", "1")
    live, src = xcom_live_status(dl, dl.global_config)
    assert live is True and src == "ENV"


def test_ready_false_when_snoozed(dl):
    # global snooze
    dl.system.set_var("global_snooze_until", time.time() + 60)
    ok, why = xcom_ready(dl, cfg=dl.global_config)
    assert ok is False and "snoozed" in why


def test_ready_false_when_voice_cooldown(dl):
    dl.system.set_var("voice_cooldown_until", time.time() + 90)
    ok, why = xcom_ready(dl, cfg=dl.global_config)
    assert ok is False and "voice_cooldown" in why


def test_guard_requires_trigger(dl):
    ok, why = xcom_guard(dl, triggered=False, cfg=dl.global_config)
    assert ok is False and why == "not_triggered"


def test_voice_cooldown_set_and_read(dl):
    # idle → zero
    rem0, eta0 = read_voice_cooldown_remaining(dl)
    assert rem0 == 0 and eta0 is None
    # set → positive
    set_voice_cooldown(dl, 45)
    rem1, eta1 = read_voice_cooldown_remaining(dl)
    assert 1 <= rem1 <= 45 and eta1 is not None
    # clear → zero
    set_voice_cooldown(dl, 0)
    rem2, eta2 = read_voice_cooldown_remaining(dl)
    assert rem2 == 0 and eta2 is None


def test_snooze_reader_defaults(dl):
    # idle → zero
    rem, eta = read_snooze_remaining(dl)
    assert rem == 0 and eta is None


def test_interval_prefers_file_then_env(dl, monkeypatch):
    # Prefer FILE
    dl.global_config.setdefault("monitor", {})["loop_seconds"] = 33
    assert get_sonic_interval(dl) == 33
    # Clear FILE → fall back to ENV
    dl.global_config.clear()
    monkeypatch.setenv("SONIC_MONITOR_INTERVAL", "44")
    assert get_sonic_interval(dl) == 44


def test_default_voice_cooldown_from_cfg(dl, monkeypatch):
    dl.global_config.setdefault("channels", {}).setdefault("voice", {})["cooldown_seconds"] = 200
    assert get_default_voice_cooldown(dl.global_config) == 200
    # ENV override when no FILE
    dl.global_config.clear()
    monkeypatch.setenv("VOICE_COOLDOWN_SECONDS", "120")
    assert get_default_voice_cooldown(None) == 120
