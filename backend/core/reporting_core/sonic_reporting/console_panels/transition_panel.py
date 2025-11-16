# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import os
import shutil
import sys
import time
from typing import Any, Dict, Optional

DEFAULT_POLL_SECONDS = 30
DEFAULT_FPS = 12
DEFAULT_RUNNER = "ping_pong_bar"


def _get_interval_s(ctx: Optional[Dict[str, Any]]) -> int:
    """
    Resolve the poll interval (seconds) from:
      1) ctx["poll_interval_s"], if present
      2) env SONIC_POLL_SECONDS
      3) DEFAULT_POLL_SECONDS
    """
    val: Optional[Any] = None
    if isinstance(ctx, dict):
        val = ctx.get("poll_interval_s")

    if val is None:
        val = os.getenv("SONIC_POLL_SECONDS")

    try:
        interval = int(val)
    except Exception:
        interval = DEFAULT_POLL_SECONDS

    return max(0, interval)


def _get_runner_name(ctx: Optional[Dict[str, Any]]) -> str:
    """
    Resolve which fun_core transition runner to use.

    Priority:
      1) ctx["transition_runner"]
      2) env SONIC_TRANSITION_RUNNER
      3) DEFAULT_RUNNER
    """
    if isinstance(ctx, dict):
        name = ctx.get("transition_runner")
        if isinstance(name, str) and name.strip():
            return name.strip()

    name = os.getenv("SONIC_TRANSITION_RUNNER", DEFAULT_RUNNER)
    return name.strip() or DEFAULT_RUNNER


def _term_width() -> int:
    try:
        return shutil.get_terminal_size((80, 20)).columns
    except Exception:
        return 80


def _run_simple_countdown(duration: int) -> None:
    """Fallback: single-line text countdown (no fun_core dependency)."""
    width = _term_width()
    for remaining in range(duration, 0, -1):
        msg = f"⏱ next poll in {remaining:>2d}s"
        line = msg.ljust(width)
        try:
            sys.stdout.write("\r" + line)
            sys.stdout.flush()
        except Exception:
            break
        time.sleep(1)

    try:
        sys.stdout.write("\r" + (" " * width) + "\r")
        sys.stdout.flush()
    except Exception:
        pass


def run(ctx: Optional[Dict[str, Any]] = None) -> None:
    """
    Fun-zone transition used between Sonic Monitor cycles.

    Prefers a fun_core transition runner (fortune_timer by default) which shows
    a playful timer + one-liner. If fun_core cannot be imported for any reason,
    falls back to the simple text countdown used previously.
    """
    duration = _get_interval_s(ctx)
    if duration <= 0:
        return

    # First try the fun_core transition path
    try:
        runner_name = _get_runner_name(ctx)

        mod = importlib.import_module(
            f"backend.core.fun_core.transitions.runners.{runner_name}"
        )
        Runner = getattr(mod, "Runner")
        runner = Runner()

        from backend.core.fun_core.transitions.base import TransitionContext
        from backend.core.fun_core.transitions import themes as T

        fps_val: Optional[Any] = None
        if isinstance(ctx, dict):
            fps_val = ctx.get("transition_fps") or ctx.get("fps")

        try:
            fps = int(fps_val) if fps_val is not None else int(
                os.getenv("SONIC_TRANSITION_FPS", str(DEFAULT_FPS))
            )
        except Exception:
            fps = DEFAULT_FPS

        width = 0
        height = 0
        if isinstance(ctx, dict):
            try:
                width = int(ctx.get("width", 0) or 0)
            except Exception:
                width = 0
            try:
                height = int(ctx.get("height", 0) or 0)
            except Exception:
                height = 0

        tctx = TransitionContext(
            duration_s=duration,
            fps=fps,
            width=width,
            height=height,
            title="Next cycle starts in",
            emoji=True,
            theme=getattr(T, "DEFAULT_THEME"),
            # Let the runner supply its own fun_line (fortune_timer does this).
            get_fun_line=None,
        )
        runner.run(tctx)
        return
    except Exception:
        # Best-effort only: don't break the monitor if fun_core is missing;
        # fall back to the simple countdown.
        pass

    _run_simple_countdown(duration)


if __name__ == "__main__":
    # Quick manual test: 5-second countdown
    run({"poll_interval_s": 5})
