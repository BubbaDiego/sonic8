import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.logging import log

try:  # Optional external dependency
    from playsound import playsound
except Exception:  # pragma: no cover - optional
    playsound = None


class SoundService:
    def __init__(self, sound_file="frontend/static/sounds/death_spiral.mp3"):
        """Initialize the service anchored at the repository root."""
        # Move two levels up to reach ``backend`` then one more to repo root
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.sound_file = os.path.join(base_dir, sound_file)

    def play(self, file_path: str = None):
        """
        Plays an MP3 file. If *file_path* is missing or not found,
        tries an additional fallback path under *frontend/static/sounds/*.
        """

        # Determine candidate paths
        candidates = []
        if file_path:
            candidates.append(os.path.abspath(file_path))
        # primary path (provided in constructor)
        candidates.append(self.sound_file)
        # fallback: project_root/frontend/static/sounds/<filename>
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            fname = os.path.basename(file_path) if file_path else os.path.basename(self.sound_file)
            candidates.append(os.path.join(root_dir, "frontend", "static", "sounds", fname))
        except Exception:
            pass

        path = None
        for p in candidates:
            if p and os.path.isfile(p):
                path = p
                break

        if not path:
            log.error(f"Sound file not found in any known location: {candidates}", source="SoundService")
            self._fallback_beep()
            return False

        try:
            log.info(f"🔊 Playing sound: {path}", source="SoundService")
            if sys.platform.startswith("win"):
                try:
                    os.startfile(path)  # non-blocking
                except Exception as e:
                    log.debug(f"os.startfile failed: {e}", source="SoundService")
                    if playsound:
                        playsound(path)
                    else:
                        raise
            else:
                if playsound:
                    playsound(path)
                else:
                    raise RuntimeError("playsound dependency missing")

            log.success("✅ System sound played", source="SoundService")
            return True

        except Exception as e:
            log.error(f"❌ Playback failed: {e}", source="SoundService")
            self._fallback_beep()
            return False

    def _fallback_beep(self):
        try:
            print("\a")  # ASCII bell
            log.info("Fallback beep emitted", source="SoundService")
        except Exception as e:
            log.error(f"Fallback beep failed: {e}", source="SoundService")
