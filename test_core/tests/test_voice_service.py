import types
import importlib

import pytest


def test_voice_service_failure_no_death(monkeypatch):
    vs = importlib.import_module('xcom.voice_service')

    class DummyClient:
        def __init__(self, *a, **k):
            class Calls:
                @staticmethod
                def create(*a, **k):
                    raise Exception('boom')
            self.calls = Calls()
    monkeypatch.setattr(vs, 'Client', DummyClient)

    called = {'death': False}
    flask = importlib.import_module('flask')
    flask._current_app = types.SimpleNamespace(
        system_core=types.SimpleNamespace(death=lambda *a, **k: called.__setitem__('death', True))
    )
    monkeypatch.setattr(vs, 'has_app_context', lambda: True)

    svc = vs.VoiceService({'suppress_death_on_error': True,
                           'account_sid': 'sid',
                           'auth_token': 'token',
                           'default_from_phone': 'a',
                           'default_to_phone': 'b'})
    assert svc.call('b', 'msg') is False
    assert called['death'] is False
