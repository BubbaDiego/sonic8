# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
import sys
import time
from typing import Any, Dict, Optional

DEFAULT_POLL_SECONDS = 30


def _get_interval_s(ctx: Optional[Dict[str, Any]]) -> int:
    """
    Resolve the poll interval (seconds) from:
      1) ctx["poll_interval_s"], if present
      2) env SONIC_POLL_SECONDS
      3) DEFAULT_POLL_SECONDS
    """
    val = None
    if isinstance(ctx, dict):
        val = ctx.get("poll_interval_s")

    if val is None:
        val = os.getenv("SONIC_POLL_SECONDS")

    try:
        interval = int(val)
    except Exception:
        interval = DEFAULT_POLL_SECONDS

    return max(0, interval)


def _term_width() -> int:
    try:
        return shutil.get_terminal_size((80, 20)).columns
    except Exception:
        return 80


def run(ctx: Optional[Dict[str, Any]] = None) -> None:
    """
    Simple countdown used between Sonic Monitor cycles.

    Prints a single line and updates it each second:
        ⏱ next poll in 23s …

    This is called from the Sonic engine between cycles, and can also be
    invoked directly for testing:

        python -m backend.core.reporting_core.sonic_reporting.console_panels.transition_panel
    """
    duration = _get_interval_s(ctx)
    if duration <= 0:
        return

    width = _term_width()
    # Use carriage return to rewrite the same line
    for remaining in range(duration, 0, -1):
        msg = f"⏱ next poll in {remaining:>2d}s"
        line = msg.ljust(width)
        try:
            sys.stdout.write("\r" + line)
            sys.stdout.flush()
        except Exception:
            # If stdout gets weird, just bail gracefully
            break
        time.sleep(1)

    # Clear the line before the next cycle draws panels
    try:
        sys.stdout.write("\r" + (" " * width) + "\r")
        sys.stdout.flush()
    except Exception:
        pass


if __name__ == "__main__":
    # Quick manual test: 5-second countdown
    run({"poll_interval_s": 5})
