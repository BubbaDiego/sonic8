# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
import threading
import time
from typing import Optional

_SPINNER_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

class _SpinnerThread(threading.Thread):
    def __init__(self, prefix: str, text: str, interval: float = 0.08) -> None:
        super().__init__(daemon=True)
        self.prefix = prefix
        self.text = text
        self.interval = interval
        self._stop = threading.Event()

    def run(self) -> None:
        i = 0
        while not self._stop.is_set():
            frame = _SPINNER_FRAMES[i % len(_SPINNER_FRAMES)]
            msg = f"\r{frame}  {self.prefix:<22} {self.text:<48} "
            sys.stdout.write(msg)
            sys.stdout.flush()
            time.sleep(self.interval)
            i += 1

    def stop(self, outcome_icon: str, final_text: str) -> None:
        self._stop.set()
        # clear line then print final status
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.write(f"{outcome_icon}  {self.prefix:<22} {final_text}\n")
        sys.stdout.flush()

class SonicMonitorLive:
    """
    Minimal console live UI:
      - start_spinner(phase, label) -> handle
      - stop_spinner(handle, outcome='ok', notes='', seconds=None)
    """
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = bool(enabled)

    def start_spinner(self, phase: str, label: str) -> Optional[_SpinnerThread]:
        if not self.enabled:
            return None
        t = _SpinnerThread(prefix=phase, text=label)
        t.start()
        return t

    def stop_spinner(self, handle: Optional[_SpinnerThread], outcome: str, notes: str, seconds: Optional[float]) -> None:
        if handle is None:
            return
        icon = {"ok":"✅", "warn":"⚠️", "error":"✖️", "skip":"⚪"}.get(outcome, "✅")
        tail = notes
        if seconds is not None:
            tail = f"{notes}   ({seconds:.2f}s)"
        handle.stop(icon, tail)
