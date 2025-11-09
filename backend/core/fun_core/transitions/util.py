# -*- coding: utf-8 -*-
from __future__ import annotations

import os, sys, shutil, time, contextlib
from typing import Iterable, List, Tuple

RESET = "\x1b[0m"
BOLD  = "\x1b[1m"
DIM   = "\x1b[2m"

FG_BLACK  = "\x1b[30m"
FG_RED    = "\x1b[31m"
FG_GREEN  = "\x1b[32m"
FG_YELLOW = "\x1b[33m"
FG_BLUE   = "\x1b[34m"
FG_MAG    = "\x1b[35m"
FG_CYAN   = "\x1b[36m"
FG_WHITE  = "\x1b[37m"

CLEAR = "\x1b[2J"
HOME  = "\x1b[H"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"

def enable_ansi_on_windows() -> None:
    if os.name == "nt":
        try:
            import colorama
            colorama.just_fix_windows_console()
        except Exception:
            pass

def supports_emoji() -> bool:
    # conservative: allow unless explicitly disabled
    return os.getenv("NO_EMOJI", "0") in {"0", "", None}

def console_size(default: Tuple[int,int]=(92, 26)) -> Tuple[int,int]:
    try:
        size = shutil.get_terminal_size()
        w = max(40, min(200, int(size.columns)))
        h = max(12,  min(100, int(size.lines)))
        return (w, h)
    except Exception:
        return default

@contextlib.contextmanager
def hidden_cursor():
    try:
        sys.stdout.write(HIDE_CURSOR); sys.stdout.flush()
        yield
    finally:
        sys.stdout.write(SHOW_CURSOR); sys.stdout.flush()

def clear_screen():
    sys.stdout.write(CLEAR + HOME)
    sys.stdout.flush()

def home():
    sys.stdout.write(HOME)
    sys.stdout.flush()

def clear_down():
    sys.stdout.write("\x1b[J")
    sys.stdout.flush()

def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))

def pad(s: str, w: int) -> str:
    return s if len(s) >= w else s + (" " * (w - len(s)))

def fit_lines(lines: Iterable[str], width: int) -> List[str]:
    out = []
    for ln in lines:
        text = ln.replace("\n"," ")
        if len(text) > width:
            text = text[:max(0, width-1)] + "…"
        out.append(pad(text, width))
    return out

def fps_loop(duration_s: int, fps: int):
    start = time.perf_counter()
    frame_dt = 1.0 / max(1, fps)
    i = 0
    while True:
        now = time.perf_counter()
        elapsed = now - start
        if elapsed >= duration_s:
            break
        yield i, elapsed, max(0.0, duration_s - elapsed)
        i += 1
        # sleep to next frame
        nxt = start + i * frame_dt
        delay = max(0.0, nxt - time.perf_counter())
        if delay:
            time.sleep(delay)

def seconds_to_mmss(sec: float) -> str:
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m:02d}:{s:02d}"
