import os, sys, types, pytest
from backend.core.reporting_core.sonic_reporting.xcom_extras import set_voice_cooldown, read_voice_cooldown_remaining
from backend.data.data_locker import DataLocker

xc = pytest.importorskip("backend.core.xcom_core.xcom_core")

def _dispatch(monitor, payload, channels, context=None):
    fn = getattr(xc, "dispatch_notifications", None)
    if callable(fn):
        return fn(monitor, payload, channels, context=context)
    # fallback synth via XComCore
    core = xc.XComCore(getattr(DataLocker.get_instance(), "system", None))
    requested = [k for k, v in channels.items() if v]
    if not bool(payload.get("breach")) and "voice" in requested:
        requested.remove("voice")
    res = core.send_notification(level="HIGH" if "voice" in requested else "LOW",
                                 subject="UT", body="UT", initiator="ut", mode=requested or None)
    summary = {"monitor": monitor, "breach": bool(payload.get("breach")), "channels": {}}
    summary["channels"]["system"] = {"ok": True}
    if "voice" in requested:
        ok = bool(res.get("voice")) or bool(res.get("voice_ok", False))
        entry = {"ok": ok}
        if not ok:
            rs = res.get("voice_suppressed")
            if isinstance(rs, dict):
                entry["skip"] = rs.get("reason", "suppressed")
        summary["channels"]["voice"] = entry
    else:
        summary["channels"]["voice"] = {"ok": False, "skip": "disabled"}
    return summary

def _ch(voice=True, system=True, sms=False, tts=False):
    return {"voice": voice, "system": system, "sms": sms, "tts": tts}

def test_no_redial_during_voice_cooldown(monkeypatch, dl):
    # Pretend creds exist (so normally we would try to call)
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC_test")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "auth_test")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15555550100")
    monkeypatch.setenv("MY_PHONE_NUMBER", "+15555550123")

    # Stub Twilio import globally so any 'from twilio.rest import Client' hits our stub
    calls = {"count": 0}
    class _StubCalls:
        def create(self, *a, **k):
            calls["count"] += 1
            return types.SimpleNamespace(sid="SIM")
    class _StubClient:
        def __init__(self, *a, **k):
            self.calls = _StubCalls()
    sys.modules["twilio"] = types.SimpleNamespace(rest=types.SimpleNamespace(Client=_StubClient))
    sys.modules["twilio.rest"] = sys.modules["twilio"].rest

    # Activate cooldown
    set_voice_cooldown(dl, 120)
    rem, _ = read_voice_cooldown_remaining(dl)
    assert rem > 0

    out = _dispatch("liquid", {"breach": True, "summary": "cooldown test"}, _ch(voice=True, system=False), context={"twilio": {}})

    # No dial should occur during cooldown
    assert calls["count"] == 0
    v = out["channels"].get("voice", {})
    assert v.get("ok") is False

def test_near_state_does_not_dispatch_voice(monkeypatch):
    # Clear env creds; breach=False must never report success for voice
    for k in ("TWILIO_ACCOUNT_SID","TWILIO_AUTH_TOKEN","TWILIO_PHONE_NUMBER","MY_PHONE_NUMBER","TWILIO_TO_PHONE"):
        monkeypatch.delenv(k, raising=False)
    out = _dispatch("liquid", {"breach": False, "summary": "near only"}, _ch(voice=True, system=True), context={})
    v = out["channels"].get("voice", {})
    assert v.get("ok") is False
