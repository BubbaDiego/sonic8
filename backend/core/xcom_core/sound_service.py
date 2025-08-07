"""SoundService plays MP3 alerts using playsound; install the "playsound" package for full audio support."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.logging import log

try:  # Optional external dependency
    from playsound import playsound
except Exception:  # pragma: no cover - optional
    playsound = None


class SoundService:
    def __init__(self, sound_file="frontend/static/sounds/death_spiral.mp3"):
        """Initialize the service anchored at the repository root."""
        # Move four levels up from this file to reach the repository root
        self.root_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        self.sound_file = os.path.join(self.root_dir, sound_file)

    def play(self, file_path: str = None):
        """
        Plays an MP3 file. If *file_path* is missing or not found,
        tries an additional fallback path under *frontend/static/sounds/*.
        """

        # Determine candidate paths
        candidates = []
        if file_path:
            # absolute path relative to current working directory
            candidates.append(os.path.abspath(file_path))
            # attempt repository-root-relative path if provided path is relative
            if not os.path.isabs(file_path):
                candidates.append(os.path.join(self.root_dir, file_path))
            fname = os.path.basename(file_path)
        else:
            fname = os.path.basename(self.sound_file)
        # fallback: project_root/frontend/static/sounds/<filename>
        candidates.append(
            os.path.join(self.root_dir, "frontend", "static", "sounds", fname)
        )
        # default path (provided in constructor)
        candidates.append(self.sound_file)

        path = None
        for p in candidates:
            if p and os.path.isfile(p):
                path = p
                break

        if not path:
            log.error(
                f"Sound file not found in any known location: {candidates}",
                source="SoundService",
            )
            self._fallback_beep()
            return False

        try:
            log.info(f"🔊 Playing sound: {path}", source="SoundService")

            if playsound:
                playsound(path)
            else:
                raise RuntimeError("playsound dependency missing. Install the 'playsound' package for MP3 playback")

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
