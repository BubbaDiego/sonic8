from __future__ import annotations
import random
import sys
import threading
import time
from typing import List, Optional

from .config import SPINNERS, SPINNER_INTERVAL, MIN_SPINNER_SECONDS


class _SpinnerThread:
    def __init__(self, prefix: str, frames: List[str]) -> None:
        self.prefix = prefix
        self.frames = frames or ["·", "∙", "●", "∙"]
        self.stop = threading.Event()
        self.started_at = time.perf_counter()
        self._t: Optional[threading.Thread] = None
        self._last_len = 0

    def start(self) -> None:
        def _run() -> None:
            i = 0
            while not self.stop.is_set():
                frame = self.frames[i % len(self.frames)]
                line = f"{self.prefix}{frame}"
                sys.stdout.write("\r" + line + " " * max(self._last_len - len(line), 0))
                sys.stdout.flush()
                self._last_len = len(line)
                i += 1
                time.sleep(SPINNER_INTERVAL)

        self._t = threading.Thread(target=_run, daemon=True)
        self._t.start()

    def stop_and_wait_min(self) -> float:
        while (time.perf_counter() - self.started_at) < MIN_SPINNER_SECONDS:
            time.sleep(0.02)
        self.stop.set()
        if self._t and self._t.is_alive():
            self._t.join(timeout=0.25)
        sys.stdout.write("\r")
        sys.stdout.flush()
        return time.perf_counter() - self.started_at


def pick_spinner() -> List[str]:
    try:
        return random.choice(SPINNERS)
    except Exception:
        return ["·", "∙", "●", "∙"]
