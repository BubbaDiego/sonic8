
try:
    import pyttsx3
except Exception:  # pragma: no cover - optional dependency
    pyttsx3 = None
import sys
from backend.core.logging import log

class TTSService:
    def __init__(self, voice_name: str | None = None):
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

    def send(self, recipient: str, body: str) -> bool:
        if not self.engine:
            log.warning("pyttsx3 not available", source="TTSService")
            return False
        try:
            self.engine.say(body)
            self.engine.runAndWait()
            log.success("✅ TTS message delivered successfully", source="TTSService")
            return True
        except Exception as e:
            log.error(f"❌ TTS delivery failed: {e}", source="TTSService")
            return False
