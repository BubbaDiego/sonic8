
try:
    import pyttsx3
except Exception:  # pragma: no cover - optional dependency
    pyttsx3 = None
import sys
from backend.core.logging import log
from backend.core.reporting_core.xcom_reporter import (
    twilio_fail,
    twilio_start,
    twilio_success,
)

class TTSService:
    def __init__(self, voice_name: str | None = None, speed: int | None = None):
        driver = "sapi5" if sys.platform == "win32" else None
        if pyttsx3:
            try:
                self.engine = pyttsx3.init(driver)
            except Exception as e:  # pragma: no cover - initialization failure
                log.warning(
                    f"⚠️ pyttsx3 driver unavailable: {e}", source="TTSService"
                )
                self.engine = None
        else:
            self.engine = None
            log.warning("pyttsx3 not installed; TTS disabled", source="TTSService")

        if voice_name and self.engine:
            for v in self.engine.getProperty("voices"):
                if voice_name.lower() in v.name.lower():
                    self.engine.setProperty("voice", v.id)
                    log.info(f"TTS Voice set to {v.name}", source="TTSService")
                    break

        if speed is not None and self.engine:
            try:
                self.engine.setProperty("rate", speed)
                log.info(f"TTS speed set to {speed}", source="TTSService")
            except Exception as e:  # pragma: no cover - optional configuration
                log.warning(
                    f"⚠️ Failed to set TTS speed: {e}", source="TTSService"
                )

    def send(self, recipient: str, body: str) -> bool:
        twilio_start("tts", recipient, "-")
        if not self.engine:
            log.warning("pyttsx3 not available", source="TTSService")
            twilio_fail("tts", RuntimeError("pyttsx3 engine unavailable"))
            return False
        try:
            self.engine.say(body)
            self.engine.runAndWait()
            log.success("✅ TTS message delivered successfully", source="TTSService")
            twilio_success("tts", note="spoken")
            return True
        except Exception as e:
            log.error(f"❌ TTS delivery failed: {e}", source="TTSService")
            twilio_fail("tts", e)
            return False
