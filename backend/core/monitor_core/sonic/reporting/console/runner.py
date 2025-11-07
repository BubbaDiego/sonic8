# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Callable

def _safe_render(mod_name: str, fn_name: str, dl: Any) -> None:
    try:
        mod = __import__(mod_name, fromlist=[fn_name])
        fn: Callable = getattr(mod, fn_name)
        try:
            fn(dl)               # preferred signature
        except TypeError:
            fn(dl, None)         # tolerate old (dl, csum)
    except Exception as e:
        print(f"[REPORT] {mod_name}.{fn_name} failed: {e}")

def run_console_reporters(dl: Any, debug: bool = False) -> None:
    # Order: cycle activity first, then monitors, positions, wallets, raydium
    _safe_render("backend.core.reporting_core.sonic_reporting.cycle_activity_reporter", "render", dl)
    _safe_render("backend.core.reporting_core.sonic_reporting.monitor_panel", "render", dl)
    _safe_render("backend.core.reporting_core.sonic_reporting.positions_panel", "render", dl)
    _safe_render("backend.core.reporting_core.sonic_reporting.wallets_panel", "render", dl)
    _safe_render("backend.core.reporting_core.sonic_reporting.raydium_panel", "render", dl)
