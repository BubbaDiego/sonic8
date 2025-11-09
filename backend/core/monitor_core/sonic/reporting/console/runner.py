# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable, Optional
import importlib
import os
import time


def _safe_render(mod_name: str, fn_name: str, dl: Any) -> None:
    """Call a classic panel render(dl[, csum]) and ignore failures."""
    try:
        mod = importlib.import_module(mod_name)
        fn: Callable = getattr(mod, fn_name)
        try:
            fn(dl)  # preferred signature
        except TypeError:
            fn(dl, None)  # tolerate old (dl, csum)
    except Exception as e:
        print(f"[REPORT] {mod_name}.{fn_name} failed: {e}")


def _render_footer_panel(footer_ctx: Optional[dict]) -> None:
    """
    Import the new cycle_footer_panel and print its returned lines (list[str]).
    It accepts either render(context_dict) or keyword args; we pass a dict.
    """
    try:
        mod = importlib.import_module(
            "backend.core.reporting_core.sonic_reporting.cycle_footer_panel"
        )
        fn = getattr(mod, "render", None)
        if callable(fn):
            res = fn(footer_ctx or {})
            if isinstance(res, (list, tuple)):
                for line in res:
                    print(line)
            elif isinstance(res, str):
                print(res)
    except Exception as e:
        print(f"[REPORT] cycle_footer_panel.render failed: {e}")


def run_console_reporters(
    dl: Any,
    debug: bool = False,
    *,
    footer_ctx: Optional[dict] = None,
) -> None:
    """
    Final ordering:
      1) Cycle Activity
      2) Prices (reporter stack)
      3) Positions (reporter stack)
      4) Monitors
      5) XCom
      6) Wallets
      7) Cycle footer (always last)
    """
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.cycle_activity_reporter",
        "render",
        dl,
    )

    # Reporter panels (Prices, Positions, XCom, Wallets) now live between Activity and Monitors
    try:
        from backend.core.reporting_core import console_reporter as _cr

        try:
            width = int(os.environ.get("SONIC_CONSOLE_WIDTH", "92"))
        except Exception:
            width = 92

        ctx = {
            "loop_counter": int((footer_ctx or {}).get("loop_counter", 0)),
            "poll_interval_s": int((footer_ctx or {}).get("poll_interval_s", 0)),
            "total_elapsed_s": float((footer_ctx or {}).get("total_elapsed_s", 0.0)),
            "ts": (footer_ctx or {}).get("ts", time.time()),
        }

        print("\n[REPORT] panel runner: BEGIN", flush=True)
        modules: list[str] = []
        if hasattr(_cr, "_get_panel_modules"):
            try:
                modules = list(_cr._get_panel_modules())
            except Exception:
                modules = []
        elif hasattr(_cr, "PANEL_MODULES"):
            modules = list(getattr(_cr, "PANEL_MODULES") or [])
        modules_line = ", ".join(str(m) for m in modules) if modules else "<none>"
        print(f"[REPORT] panel modules: {modules_line}", flush=True)
        _cr.render_panel_stack(ctx=ctx, dl=dl, width=width, writer=print)
        print("[REPORT] panel runner: END\n", flush=True)
    except Exception as exc:
        print(f"[REPORT] panel runner failed: {exc!r}", flush=True)

    _safe_render(
        "backend.core.reporting_core.sonic_reporting.monitor_panel",
        "render",
        dl,
    )
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.xcom_panel",
        "render",
        dl,
    )
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.wallets_panel",
        "render",
        dl,
    )

    # Footer box at the very end
    _render_footer_panel(footer_ctx)
