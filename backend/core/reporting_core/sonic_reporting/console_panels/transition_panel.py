from __future__ import annotations

import importlib
import os
from typing import Any, Dict


def _int(x, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _get_interval_s(ctx: Dict[str, Any]) -> int:
    """Resolve the poll interval from context or environment."""
    return (
        _int(ctx.get("poll_interval_s"))
        or _int(os.getenv("SONIC_POLL_SECONDS"))
        or 30
    )


def run(ctx: Dict[str, Any]) -> None:
    """Run the ping-pong transition for the current poll interval."""
    try:
        duration = _get_interval_s(ctx)
        if duration <= 0:
            return

        mod = importlib.import_module(
            "backend.core.fun_core.transitions.runners.ping_pong_bar"
        )
        Runner = getattr(mod, "Runner")
        runner = Runner()

        from backend.core.fun_core.transitions.base import TransitionContext
        from backend.core.fun_core.transitions import themes as T

        fps = _int(ctx.get("transition_fps") or os.getenv("SONIC_TRANSITION_FPS", 15), 15)

        tctx = TransitionContext(
            duration_s=duration,
            fps=fps,
            width=_int(ctx.get("width"), 0),
            height=_int(ctx.get("height"), 0),
            title="",
            emoji=True,
            theme=getattr(T, "DEFAULT_THEME"),
            get_fun_line=None,
        )
        runner.run(tctx)
    except Exception:
        import time

        time.sleep(_get_interval_s(ctx))
