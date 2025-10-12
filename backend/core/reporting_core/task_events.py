from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, Optional

from .spinner import _SpinnerThread, pick_spinner

Verdict = str  # "ok" | "fail" | "warn" | "skip"

_ICONS = {"ok": "✅", "fail": "❌", "warn": "⚠️", "skip": "⏭"}
_START_ICON = "▶️"


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
