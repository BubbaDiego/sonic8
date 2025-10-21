from __future__ import annotations

import itertools
import random
import shutil
import sys
import threading
import time
from typing import Dict, Iterable, Iterator, List, Optional

from .config import MIN_SPINNER_SECONDS, SPINNER_INTERVAL, SPINNERS


SPINSETS: Dict[str, List[str]] = {
    "line": list("|/-\\"),
    "pipe": ["┤", "┘", "┴", "└", "├", "┌", "┬", "┐"],
    "moon": ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"],
    "arrow": ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
    "bar": [
        "▁",
        "▂",
        "▃",
        "▄",
        "▅",
        "▆",
        "▇",
        "█",
        "▇",
        "▆",
        "▅",
        "▄",
        "▃",
        "▂",
    ],
    "clock": [
        "🕛",
        "🕐",
        "🕑",
        "🕒",
        "🕓",
        "🕔",
        "🕕",
        "🕖",
        "🕗",
        "🕘",
        "🕙",
        "🕚",
    ],
}

ORDER: tuple[str, ...] = ("line", "pipe", "moon", "arrow", "bar", "clock")


def _frames(style: str | None) -> Iterator[str]:
    frames: Iterable[str] = SPINSETS.get(style or "", [])
    if not frames:
        frames = SPINSETS["line"]
    return itertools.cycle(frames)


def style_for_cycle(index: Optional[int]) -> str:
    if not ORDER:
        return "line"
    try:
        if index is None:
            raise ValueError
        return ORDER[int(index) % len(ORDER)]
    except Exception:
        return ORDER[0]


def _term_width(default: int = 80) -> int:
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return default


def spin_progress(seconds: float, *, style: str = "line", label: str = "") -> None:
    """
    Spinner + progress bar during sleep.
    - Uses only stdlib; auto-falls back to plain sleep when not a TTY.
    - Clears its line at the end; Ctrl+C propagates.
    """
    if seconds <= 0:
        return
    if not sys.stdout.isatty():
        time.sleep(seconds)
        return

    frames = _frames(style)
    width = max(20, _term_width() - len(label) - 28)
    start = time.perf_counter()
    end = start + seconds
    last_fill = -1

    try:
        while True:
            now = time.perf_counter()
            remaining = end - now
            if remaining <= 0:
                break
            frac = 1.0 - (remaining / seconds)
            fill = int(frac * width)
            if fill != last_fill:
                bar = "█" * fill + "░" * (width - fill)
                frame = next(frames)
                elapsed = int(seconds * frac)
                rem = int(remaining + 0.999)
                mins, secs = divmod(rem, 60)
                msg = (
                    f"\r{frame} {label} [{bar}] {elapsed:>3}s/{int(seconds):<3}s  "
                    f"(eta {mins:02d}:{secs:02d})"
                )
                sys.stdout.write(msg)
                sys.stdout.flush()
                last_fill = fill
            time.sleep(0.1)
    except KeyboardInterrupt:
        sys.stdout.write("\r" + " " * (width + 64) + "\r")
        sys.stdout.flush()
        raise
    sys.stdout.write("\r" + " " * (width + 64) + "\r")
    sys.stdout.flush()


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
