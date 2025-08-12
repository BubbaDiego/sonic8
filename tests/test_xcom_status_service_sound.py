import sys
import types

import pytest


# Stub "twilio" module so importing xcom_status_service doesn't require the actual dependency
twilio_stub = types.ModuleType("twilio")
twilio_rest_stub = types.ModuleType("rest")
twilio_rest_stub.Client = object
twilio_stub.rest = twilio_rest_stub
sys.modules.setdefault("twilio", twilio_stub)
sys.modules.setdefault("twilio.rest", twilio_rest_stub)
twilio_twiml_stub = types.ModuleType("twiml")
twilio_voice_response_stub = types.ModuleType("voice_response")
twilio_voice_response_stub.VoiceResponse = object
twilio_twiml_stub.voice_response = twilio_voice_response_stub
sys.modules.setdefault("twilio.twiml", twilio_twiml_stub)
sys.modules.setdefault("twilio.twiml.voice_response", twilio_voice_response_stub)
sys.modules.setdefault("requests", types.ModuleType("requests"))

from backend.services import xcom_status_service


def test_probe_sound_ok(monkeypatch):
    """Sound probe returns 'ok' when playback succeeds."""
    monkeypatch.setattr(xcom_status_service.SoundService, "play", lambda self: True)
    svc = xcom_status_service.XComStatusService({})
    assert svc.probe_sound() == "ok"


def test_probe_sound_failure(monkeypatch):
    """Sound probe reports failure when playback returns False."""
    monkeypatch.setattr(xcom_status_service.SoundService, "play", lambda self: False)
    svc = xcom_status_service.XComStatusService({})
    assert svc.probe_sound() == "playback failed"


def test_probe_sound_missing_dependency(monkeypatch):
    """Sound probe indicates missing dependency if playsound is unavailable."""

    def _raise(_self):
        raise ModuleNotFoundError("playsound")

    monkeypatch.setattr(xcom_status_service.SoundService, "play", _raise)
    svc = xcom_status_service.XComStatusService({})
    assert svc.probe_sound() == "playsound missing"


def test_probe_all_handles_sound_failure(monkeypatch):
    """probe_all should handle non-'ok' sound responses without crashing."""
    monkeypatch.setattr(xcom_status_service.SoundService, "play", lambda self: False)
    monkeypatch.setattr(
        xcom_status_service.XComStatusService, "probe_smtp", lambda self: "ok"
    )
    monkeypatch.setattr(
        xcom_status_service.XComStatusService, "probe_twilio", lambda self: "ok"
    )
    svc = xcom_status_service.XComStatusService({})
    result = svc.probe_all(include_sound=True)
    assert result["sound"] == "playback failed"

