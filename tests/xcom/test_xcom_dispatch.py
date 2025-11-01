import types
import pytest

xc = pytest.importorskip("backend.core.xcom_core.xcom_core")


@pytest.fixture
def no_twilio(monkeypatch):
    # ensure the dispatcher thinks creds are missing (prevents any call attempt)
    monkeypatch.setattr(
        xc,
        "_twilio_collect_creds",
        lambda *a, **k: (False, {}, "missing"),
        raising=True,
    )


def _ch(voice=True, system=True, sms=False, tts=False):
    return {"voice": voice, "system": system, "sms": sms, "tts": tts}


def test_dispatch_no_breach_never_ok_voice(no_twilio):
    out = xc.dispatch_notifications(
        "liquid",
        {"breach": False},
        _ch(voice=True, system=True),
        context={},
    )
    assert out["breach"] is False
    # voice must not succeed; with our stub it should be a SKIP (missing creds)
    v = out["channels"].get("voice", {})
    assert v.get("ok") is False and v.get("skip") in {"twilio_missing_creds", "disabled"}
    # system remains best-effort ok
    assert out["channels"]["system"]["ok"] is True


def test_dispatch_breach_voice_disabled(no_twilio):
    out = xc.dispatch_notifications(
        "liquid",
        {"breach": True},
        _ch(voice=False, system=True),
        context={}
    )
    v = out["channels"].get("voice", {})
    assert v.get("ok") is False and v.get("skip") == "disabled"
    assert out["channels"]["system"]["ok"] is True


def test_dispatch_breach_voice_enabled_but_missing_creds(no_twilio):
    out = xc.dispatch_notifications(
        "liquid",
        {"breach": True},
        _ch(voice=True, system=False),
        context={},
    )
    v = out["channels"]["voice"]
    assert v.get("ok") is False and v.get("skip") == "twilio_missing_creds"


def test_dispatch_channel_shape(no_twilio):
    out = xc.dispatch_notifications(
        "liquid",
        {"breach": True},
        _ch(voice=True, system=True, sms=True, tts=True),
        context={},
    )
    # All channels present with structured result keys
    for k in ("voice", "system", "sms", "tts"):
        assert k in out["channels"]
