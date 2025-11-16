
import sys
from typing import Optional

try:
    import pyttsx3
except Exception:  # pragma: no cover - optional dependency
    pyttsx3 = None

from backend.core.logging import log
from backend.core.reporting_core.xcom_reporter import (
    twilio_fail,
    twilio_start,
    twilio_success,
)
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_ready

from .voice_profiles import VoiceProfile

class TTSService:
    def __init__(self, voice_name: str | None = None, speed: int | None = None):
        driver = "sapi5" if sys.platform == "win32" else None
        self._engine = None
        if pyttsx3:
            try:
                self._engine = pyttsx3.init(driver)
            except Exception as e:  # pragma: no cover - initialization failure
                log.warning(
                    f"⚠️ pyttsx3 driver unavailable: {e}", source="TTSService"
                )
        else:
            log.warning("pyttsx3 not installed; TTS disabled", source="TTSService")
        self.engine = self._engine  # backwards compatibility

        if voice_name and self._engine:
            for v in self._engine.getProperty("voices"):
                if voice_name.lower() in getattr(v, "name", "").lower():
                    self._engine.setProperty("voice", v.id)
                    log.info(f"TTS Voice set to {getattr(v, 'name', v.id)}", source="TTSService")
                    break

        if speed is not None and self._engine:
            try:
                self._engine.setProperty("rate", speed)
                log.info(f"TTS speed set to {speed}", source="TTSService")
            except Exception as e:  # pragma: no cover - optional configuration
                log.warning(
                    f"⚠️ Failed to set TTS speed: {e}", source="TTSService"
                )

    def apply_voice_profile(self, profile: Optional[VoiceProfile]) -> None:
        """Configure the underlying engine from a voice profile."""

        if profile is None or not self._engine:
            return

        engine = self._engine
        try:
            if profile.tts_voice_name:
                desired = profile.tts_voice_name.lower()
                for v in engine.getProperty("voices"):
                    name = getattr(v, "name", "")
                    if desired in (v.id.lower(), name.lower()):
                        engine.setProperty("voice", v.id)
                        break
            if profile.tts_rate:
                base_rate = engine.getProperty("rate")
                engine.setProperty("rate", int(base_rate * profile.tts_rate))
            if profile.tts_volume:
                engine.setProperty("volume", float(profile.tts_volume))
        except Exception:
            pass

    def speak(self, text: str, profile: Optional[VoiceProfile] = None) -> None:
        """Speak text using the optional voice profile."""

        if not self._engine:
            raise RuntimeError("pyttsx3 engine unavailable")
        self.apply_voice_profile(profile)
        self._engine.say(text)
        self._engine.runAndWait()

    def _xcom_allowed(self, dl=None) -> bool:
        cfg = getattr(dl, "global_config", None) if dl else None
        ok, why = xcom_ready(dl, cfg=cfg)
        if not ok:
            log.debug("TTSService suppressed: %s", why, source="TTSService")
        return ok

    def send(self, recipient: str, body: str, dl=None) -> bool:
        if not self._xcom_allowed(dl):
            return False
        twilio_start("tts")
        if not self._engine:
            log.warning("pyttsx3 not available", source="TTSService")
            twilio_fail("tts", RuntimeError("pyttsx3 engine unavailable"))
            return False
        try:
            self.speak(body)
            log.success("✅ TTS message delivered successfully", source="TTSService")
            twilio_success("tts", note="spoken")
            return True
        except Exception as e:
            log.error(f"❌ TTS delivery failed: {e}", source="TTSService")
            twilio_fail("tts", e)
            return False
