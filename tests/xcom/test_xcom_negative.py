import os
import types

import pytest

from backend.core.reporting_core.sonic_reporting.xcom_extras import (
    read_voice_cooldown_remaining,
    set_voice_cooldown,
)


xc = pytest.importorskip("backend.core.xcom_core.xcom_core")


def _ch(voice=True, system=True, sms=False, tts=False):
    return {"voice": voice, "system": system, "sms": sms, "tts": tts}


def test_no_redial_during_voice_cooldown(monkeypatch, dl, tmp_path):
    """
    With valid-ish Twilio creds and voice enabled, if a cooldown window is active
    then dispatch() must NOT attempt a call (no network), and voice result is non-success.
    """

    # Pretend creds exist so the dispatcher would normally proceed.
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC_test")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "auth_test")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15555550100")
    monkeypatch.setenv("MY_PHONE_NUMBER", "+15555550123")

    # Stub Twilio client to prove no call attempt occurs
    calls = {"count": 0, "args": None}

    class _StubCalls:
        def create(self, *a, **k):  # would be called if cooldown were ignored
            calls["count"] += 1
            calls["args"] = (a, k)
            return types.SimpleNamespace(sid="SIM")

    class _StubClient:
        def __init__(self, *a, **k):
            self.calls = _StubCalls()

    monkeypatch.setitem(xc.__dict__, "Client", _StubClient, raising=False)

    # Cooldown ON
    set_voice_cooldown(dl, 120)
    rem, _ = read_voice_cooldown_remaining(dl)
    assert rem > 0

    out = xc.dispatch_notifications(
        "liquid",
        {"breach": True, "summary": "cooldown test"},
        _ch(voice=True, system=False, sms=False, tts=False),
        context={"twilio": {}},  # allow dispatcher path to think creds resolved
    )

    # Assert: no dial was attempted, voice not OK
    assert calls["count"] == 0
    v = out["channels"].get("voice", {})
    assert v.get("ok") is False
    # Reason may vary by implementation (e.g., "voice_cooldown" or "xcom-not-ready")
    assert v.get("skip") or v.get("reason") or v.get("error")


def test_near_state_does_not_dispatch_voice(monkeypatch):
    """
    Orchestrator passes breach=False when all severities are 'near';
    dispatcher must NOT claim voice success. (System channel may still be OK.)
    """

    # Make sure no creds leak in from env
    for k in (
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "MY_PHONE_NUMBER",
    ):
        monkeypatch.delenv(k, raising=False)

    out = xc.dispatch_notifications(
        "liquid",
        {"breach": False, "summary": "near only"},
        _ch(voice=True, system=True, sms=False, tts=False),
        context={},
    )
    v = out["channels"].get("voice", {})
    assert v.get("ok") is False  # never success on non-breach payloads
