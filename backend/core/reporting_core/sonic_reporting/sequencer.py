# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional

# Titles/spacing
try:
    from .writer import write_line
except Exception:
    def write_line(s: str) -> None:
        print(s)

# Optional logger
try:
    from backend.core.logging import log as _log  # type: ignore
except Exception:
    _log = None  # type: ignore


def _try_render_one(module_name: str, *, fn_name: str = "render", **kwargs) -> bool:
    """
    Import and render a single module; return True on success.
    Prints a short banner so you know exactly which file was used.
    """
    try:
        from importlib import import_module
        mod = import_module(f"backend.core.reporting_core.sonic_reporting.{module_name}")
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            print(f"[SEQ] using {module_name}.{fn_name}()")
            fn(**kwargs)
            return True
        else:
            print(f"[SEQ] {module_name}.{fn_name} missing/callable=False")
            if _log:
                _log.debug("renderer function missing",
                           source="sequencer", payload={"module": module_name, "fn": fn_name})
    except Exception as e:
        print(f"[SEQ] {module_name} import failed: {e}")
        if _log:
            _log.debug("optional renderer failed",
                       source="sequencer", payload={"module": module_name, "error": str(e)})
    return False


def _try_render_candidates(candidates: list[str], *, fn_name: str = "render", **kwargs) -> Optional[str]:
    """
    Try a list of module names until one renders.
    Return the winning module name (or None).
    """
    for m in candidates:
        if _try_render_one(m, fn_name=fn_name, **kwargs):
            return m
    return None


def render_startup_banner(dl, default_json_path: Optional[str] = None) -> None:
    """
    Print the Sonic Monitor Configuration banner (LAN URLs, config mode, paths, DB).
    Called once at startup.
    """
    # Banner module is consistent in your tree.
    try:
        from .banner_panel import render_banner
        render_banner(dl, default_json_path)
    except Exception as e:
        print(f"[SEQ] banner_panel.render_banner failed: {e}")
        if _log:
            _log.debug("banner failed", source="sequencer", payload={"error": str(e)})


def render_cycle(dl, csum: Dict[str, Any], default_json_path: Optional[str] = None) -> None:
    """
    One full console cycle (tolerant imports with clear 'using X' prints):

      1) Sync Data        (title + table)
      2) Prices           (title + table)
      3) Monitors         (title + table)
      4) Positions        (title + table)
      +) Wallets panel    (optional)
      +) XCOM Check       (optional; wrapped with BEGIN/END markers)
    """

    # 1) Sync Data
    write_line("")
    write_line("---------------------- 🛠️  Sync  Data  🛠️ ----------------------")
    # Known names across branches: sync_panel | sync_data | sync_cycle | sync_activities
    _try_render_candidates(
        ["sync_panel", "sync_data", "sync_cycle", "sync_activities"],
        dl=dl, csum=csum, default_json_path=default_json_path
    )

    # 2) Prices
    write_line("")
    write_line("---------------------- 💰  Prices  ----------------------")
    # Known names: price_panel | prices_table | prices | market_prices
    _try_render_candidates(
        ["price_panel", "prices_table", "prices", "market_prices"],
        csum=csum
    )

    # 3) Monitors
    write_line("")
    write_line("---------------------- 🖥️  Monitors  ----------------------")
    # Known names: monitor_panel | evaluations_table | monitors_table | monitor_table
    _try_render_candidates(
        ["monitor_panel", "evaluations_table", "monitors_table", "monitor_table"],
        dl=dl, csum=csum
    )

    # 4) Positions
    write_line("")
    write_line("---------------------- 📈  Positions  ----------------------")
    # Known names: positions_panel | positions_snapshot | positions_snapshot_v1 | positions_debug | positions_table
    _try_render_candidates(
        ["positions_panel", "positions_snapshot", "positions_snapshot_v1", "positions_debug", "positions_table"],
        dl=dl, csum=csum
    )

    # Optional Wallets panel
    _try_render_candidates(["wallets_panel"], dl=dl)

    # XCOM Check footer with explicit BEGIN/END markers
    print("[XCOM-CHECK][BEGIN]")
    _try_render_candidates(["xcom_panel", "xcom_check_panel"],
                           dl=dl, csum=csum, default_json_path=default_json_path)
    print("[XCOM-CHECK][END]")
