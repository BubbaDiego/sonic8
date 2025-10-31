
import sys

try:
    import pyttsx3
except Exception:  # pragma: no cover - optional dependency
    pyttsx3 = None

from backend.core.logging import log
from backend.core.reporting_core.xcom_reporter import (
    twilio_fail,
    twilio_skip,
    twilio_start,
    twilio_success,
)
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_ready

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
