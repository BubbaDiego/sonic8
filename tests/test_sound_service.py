import backend.core.xcom_core.sound_service as sound_service
from backend.core.xcom_core.sound_service import SoundService


def test_play_returns_false_when_playsound_missing(monkeypatch):
    monkeypatch.setattr(sound_service, "playsound", None)

    called = {}

    def fake_beep(self):
        called["beep"] = True

    monkeypatch.setattr(SoundService, "_fallback_beep", fake_beep)

    service = SoundService()
    result = service.play()

    assert result is False
    assert "beep" in called
