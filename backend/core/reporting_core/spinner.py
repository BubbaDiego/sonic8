from __future__ import annotations

import itertools
import random
import shutil
import sys
import threading
import time
from typing import Callable, Dict, Iterable, Iterator, List, Optional

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


_console_lock = threading.Lock()


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


def _write_line(msg: str, *, last_len: int) -> int:
    """
    Redraw a single console line in-place. Returns new last_len.
    Strategy:
      1) '\r' to carriage return
      2) ANSI erase-line if supported (Windows Terminal, modern conhost), else pad spaces
      3) write message, flush
    """
    # Always CR to the start
    sys.stdout.write("\r")
    # Try VT erase line; harmless on non-VT consoles
    sys.stdout.write("\x1b[2K")
    # Write message; if ANSI not supported, pad with spaces to overwrite leftovers
    sys.stdout.write(msg)
    if last_len > len(msg):
        sys.stdout.write(" " * (last_len - len(msg)))
        sys.stdout.write("\r")  # return to start again
        sys.stdout.write(msg)
    sys.stdout.flush()
    return len(msg)


def spin_progress(
    seconds: float,
    *,
    style: str = "line",
    label: str = "sleep",
    bar_colorizer: Optional[Callable[[str], str]] = None,
) -> None:
    """
    Spinner + progress bar during sleep (single-line, in-place).
    - Clears the line each tick so output never wraps.
    - Auto-falls back to plain sleep when stdout is not a TTY.
    """
    if seconds <= 0:
        return
    if not sys.stdout.isatty():
        time.sleep(seconds)
        return

    frames = _frames(style)           # existing generator from this module
    width  = max(16, _term_width() - 28 - len(label))  # leave room for counters
    start  = time.perf_counter()
    end    = start + seconds
    last_fill = -1
    last_len  = 0

    # Adaptive tick ~10Hz but not too chatty; clamp for very short sleeps
    tick = 0.1 if seconds >= 5 else 0.05

    try:
        with _console_lock:
            while True:
                now = time.perf_counter()
                remaining = end - now
                if remaining <= 0:
                    break
                frac = 1.0 - (remaining / seconds)
                fill = int(frac * width)
                # update on fill change or every ~0.5s to keep the spinner lively
                if fill != last_fill or int((seconds - remaining) * 2) != int((seconds - remaining - tick) * 2):
                    bar   = "█" * fill + "░" * (width - fill)
                    if bar_colorizer is not None:
                        try:
                            bar_display = bar_colorizer(bar)
                        except Exception:
                            bar_display = bar
                        else:
                            if not isinstance(bar_display, str):
                                bar_display = str(bar_display)
                    else:
                        bar_display = bar
                    frame = next(frames)
                    elapsed = int(seconds - remaining)
                    rem     = int(remaining + 0.999)
                    mins, secs_i = divmod(rem, 60)
                    msg = (
                        f"{frame} {label} [{bar_display}] "
                        f"{elapsed:>2}s/{int(seconds):<2}s (eta {mins:02d}:{secs_i:02d})"
                    )
                    # Truncate to terminal width minus 1 to avoid accidental wrap
                    termw = _term_width()
                    if len(msg) > termw - 1:
                        msg = msg[:max(0, termw - 2)]
                    last_len = _write_line(msg, last_len=last_len)
                    last_fill = fill
                time.sleep(tick)
    except KeyboardInterrupt:
        # Clear line and propagate
        with _console_lock:
            _write_line("", last_len=last_len)  # erase
        raise
    # Final clear
    with _console_lock:
        _write_line("", last_len=last_len)


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
