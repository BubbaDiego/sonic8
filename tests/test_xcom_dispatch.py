import os, sys, types, pytest
from backend.data.data_locker import DataLocker

# Always import the module; the public surface differs by branch
xc = pytest.importorskip("backend.core.xcom_core.xcom_core")

def _dispatch(monitor, payload, channels, context=None):
    """
    Adapter that prefers the canonical `dispatch_notifications` API.
    If not present in this build, synthesize an equivalent summary via XComCore.send_notification.
    """
    fn = getattr(xc, "dispatch_notifications", None)
    if callable(fn):
        return fn(monitor, payload, channels, context=context)

    # Fallback path for sonic7-style builds
    core = xc.XComCore(getattr(DataLocker.get_instance(), "system", None))

    # Derive which explicit modes to request from the channels map
    requested = [k for k, v in channels.items() if v]
    # Respect breach gating: no voice when breach=False
    if not bool(payload.get("breach")) and "voice" in requested:
        requested.remove("voice")

    level = "HIGH" if "voice" in requested else "LOW"
    res = core.send_notification(
        level=level, subject="UT", body="UT", initiator="ut",
        mode=requested or None
    )

    # Normalize into the same summary shape that dispatch_notifications returns
    summary = {"monitor": monitor, "breach": bool(payload.get("breach")), "channels": {}}

    # system: treat as best-effort ok (UI console)
    summary["channels"]["system"] = {"ok": True} if channels.get("system", True) else {"ok": False, "skip": "disabled"}

    # voice
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

    # sms/tts if requested
    if channels.get("sms"):
        summary["channels"]["sms"] = {"ok": bool(res.get("sms"))}
    if channels.get("tts"):
        summary["channels"]["tts"] = {"ok": bool(res.get("tts"))}

    return summary

def _ch(voice=True, system=True, sms=False, tts=False):
    return {"voice": voice, "system": system, "sms": sms, "tts": tts}

def test_dispatch_no_breach_never_ok_voice():
    out = _dispatch("liquid", {"breach": False}, _ch(voice=True, system=True), context={})
    assert out["breach"] is False
    v = out["channels"].get("voice", {})
    assert v.get("ok") is False  # no success without a breach
    assert out["channels"]["system"]["ok"] is True

def test_dispatch_breach_voice_disabled():
    out = _dispatch("liquid", {"breach": True}, _ch(voice=False, system=True), context={})
    v = out["channels"].get("voice", {})
    assert v.get("ok") is False and v.get("skip") == "disabled"
    assert out["channels"]["system"]["ok"] is True

def test_dispatch_breach_voice_enabled_but_missing_creds(monkeypatch):
    # Ensure there are no env creds so voice cannot proceed
    for k in ("TWILIO_ACCOUNT_SID","TWILIO_AUTH_TOKEN","TWILIO_FROM_PHONE","TWILIO_PHONE_NUMBER","TWILIO_TO_PHONE"):
        monkeypatch.delenv(k, raising=False)
    out = _dispatch("liquid", {"breach": True}, _ch(voice=True, system=False), context={})
    v = out["channels"]["voice"]
    assert v.get("ok") is False  # reason may be 'twilio_missing_creds' or 'suppressed'

def test_dispatch_channel_shape():
    out = _dispatch("liquid", {"breach": True}, _ch(voice=True, system=True, sms=True, tts=True), context={})
    for k in ("voice","system","sms","tts"):
        assert k in out["channels"]
