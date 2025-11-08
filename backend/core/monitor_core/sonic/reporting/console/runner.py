# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable, Optional
import importlib


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
      1) Cycle activity
      2) Positions
      3) Monitors
      4) Wallets
      5) Raydium
      6) Cycle footer (new)
    """
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.cycle_activity_reporter",
        "render",
        dl,
    )
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.positions_panel",
        "render",
        dl,
    )
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.monitor_panel",
        "render",
        dl,
    )
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.wallets_panel",
        "render",
        dl,
    )
    _safe_render(
        "backend.core.reporting_core.sonic_reporting.raydium_panel",
        "render",
        dl,
    )

    # NEW: footer box at the very end
    _render_footer_panel(footer_ctx)
