from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict

from .spinner import _SpinnerThread, pick_spinner

Verdict = str  # "ok" | "fail" | "warn" | "skip"

_ICONS = {"ok": "✅", "fail": "❌", "warn": "⚠️", "skip": "⏭"}
_START_ICON = "▶️"
_INDENT = "  "   # 2-space indent for blue-phase lines

# Cheap ANSI cyan; will be ignored by terminals that don't support it.
_CYAN = "\x1b[36m"
_RESET = "\x1b[0m"

# Blue-phase icons for section-style items
PHASE_ICON = {
    "price_sync": "📈",
    "positions_fetch": "📥",
    "positions_stale": "🧹",
    "hedges": "🛡️",
    "snapshot": "📸",
    "report": "📝",
    "sync_summary": "📦",
    "xcom_voice": "☎️",
    "xcom_sms": "📨",
    "xcom_tts": "🔊",
    "xcom_sound": "🔔",
}

# Allow forcing monochrome via env if needed
_NO_COLOR = os.getenv("SONIC_MONOCHROME", "").strip().lower() in {"1", "true", "yes"}


@dataclass
class _TaskState:
    label: str
    spinner: _SpinnerThread
    t0: float


_STATE: Dict[str, _TaskState] = {}


def task_start(key: str, label: str) -> None:
    if key in _STATE:
        try:
            task_end(key, "warn", note="overlap")
        except Exception:
            pass
    sp = _SpinnerThread(prefix=f"   {_START_ICON} {label} ", frames=pick_spinner())
    _STATE[key] = _TaskState(label=label, spinner=sp, t0=time.perf_counter())
    sp.start()


def task_end(
    key: str,
    verdict: Verdict,
    *,
    note: str | None = None,
    dur_s: float | None = None,
) -> None:
    st = _STATE.pop(key, None)
    if st is None:
        v = _ICONS.get(verdict, "•")
        msg = f"   {v} {key}"
        if dur_s is not None:
            msg += f" ({dur_s:.2f}s)"
        print(msg, flush=True)
        return

    elapsed = st.spinner.stop_and_wait_min()
    if dur_s is None:
        dur_s = elapsed

    v = _ICONS.get(verdict, "•")
    tail = f" ({dur_s:.2f}s)"
    if note:
        tail += f"  — {note}"

    print(f"   {v} {st.label}{tail}", flush=True)


# ─── Blue-phase (section header) flavor ───────────────────────────────────────
def phase_start(key: str, label: str) -> None:
    """Start a blue-phase line (indented + icon) with spinner."""
    if key in _STATE:
        try:
            phase_end(key, "warn", note="overlap")
        except Exception:
            pass
    icon = PHASE_ICON.get(key, "•")
    prefix = f"{_INDENT}{icon} "
    if not _NO_COLOR:
        prefix = f"{_CYAN}{prefix}{_RESET}"
    sp = _SpinnerThread(prefix=f"{prefix}{label} ", frames=pick_spinner())
    _STATE[key] = _TaskState(label=label, spinner=sp, t0=time.perf_counter())
    sp.start()


def phase_end(
    key: str,
    verdict: Verdict,
    *,
    note: str | None = None,
    dur_s: float | None = None,
) -> None:
    """Finish a blue-phase line with a real verdict + duration, keeping the blue style."""
    st = _STATE.pop(key, None)
    # Stop spinner and determine duration
    if st is not None:
        elapsed = st.spinner.stop_and_wait_min()
        if dur_s is None:
            dur_s = elapsed
        label = st.label
    else:
        # No state; print minimal fallback
        label = key
        if dur_s is None:
            dur_s = 0.0

    icon = PHASE_ICON.get(key, "•")
    v = _ICONS.get(verdict, "•")
    if _NO_COLOR:
        line = f"{_INDENT}{icon} {label}  {v} ({dur_s:.2f}s)"
    else:
        line = f"{_CYAN}{_INDENT}{icon} {label}{_RESET}  {v} ({dur_s:.2f}s)"
    if note:
        line += f"  — {note}"
    print(line, flush=True)
