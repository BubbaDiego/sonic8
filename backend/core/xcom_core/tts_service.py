
import pyttsx3
from backend.core.logging import log

class TTSService:
    def __init__(self, voice_name: str | None = None):
        self.engine = pyttsx3.init("sapi5")
        if voice_name:
            for v in self.engine.getProperty("voices"):
                if voice_name.lower() in v.name.lower():
                    self.engine.setProperty("voice", v.id)
                    log.info(f"TTS Voice set to {v.name}", source="TTSService")
                    break

    def send(self, recipient: str, body: str) -> bool:
        try:
            self.engine.say(body)
            self.engine.runAndWait()
            log.success("✅ TTS message delivered successfully", source="TTSService")
            return True
        except Exception as e:
            log.error(f"❌ TTS delivery failed: {e}", source="TTSService")
            return False
