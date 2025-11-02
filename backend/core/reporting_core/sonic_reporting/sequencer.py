# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from importlib import import_module

from .banner_config import render_banner
from .sync_data import render as render_sync                  # prints table only
from .prices_table import render as render_prices_table       # prints table only
from .evaluations_table import render as render_evals         # prints table only
from .positions_snapshot import render as render_positions    # prints table only
from .writer import write_line

# optional logger for tolerant panels
try:
    from backend.core.logging import log as _log  # type: ignore
except Exception:  # pragma: no cover
    _log = None  # type: ignore


def _try_render(name: str, **kwargs):
    try:
        mod = import_module(f"backend.core.reporting_core.sonic_reporting.{name}")
        render = getattr(mod, "render", None)
        if callable(render):
            render(**kwargs)
        else:
            print(f"[sequencer] {name}.render() missing")
    except Exception as e:
        print(f"[sequencer] {name} failed: {e}")


def render_startup_banner(dl, default_json_path: str) -> None:
    """Print the Sonic Monitor Configuration banner once at startup."""
    render_banner(dl, default_json_path)


def render_cycle(
    dl,
    csum: Dict[str, Any],
    *,
    default_json_path: str,
    show_monitors_summary: bool = False,
) -> None:
    """
    One full console cycle:

      1) Sync Data        (title here) + Sync table
      2) Prices           (title here) + Prices table
      3) Monitors         (title here) + Evaluations table
      4) Positions        (title here) + Positions table
      +) Polished Monitors (optional; icons match Prices)
      +) XCOM Check footer (optional; channels • readiness • cooldown • breaches)
    """

    # 1) Sync Data
    write_line("")  # spacer from previous block
    write_line("---------------------- 🛠️  Sync  Data  🛠️ ----------------------")
    render_sync(dl, csum, default_json_path)

    # 2) Prices
    write_line("")
    write_line("---------------------- 💰  Prices  ----------------------")
    render_prices_table(csum)

    # 3) Monitors
    write_line("")
    write_line("---------------------- 🖥️  Monitors  ----------------------")
    render_evals(dl, csum)

    # 💳 Wallets panel (safe, optional)
    _try_render("wallets_panel", dl=dl)

    # 4) Positions
    write_line("")
    write_line("---------------------- 📈  Positions  ----------------------")
    render_positions(dl, csum)

    # ---------- Optional polish / diagnostics (tolerant imports) ----------

    # Polished Monitors summary (left icons like Prices: 🟡/🔷/🟣)
    if show_monitors_summary:
        try:
            from .monitors_summary import render as _render_monitors_summary  # type: ignore
            write_line("")  # spacer before compact summary
            _render_monitors_summary(dl, csum, default_json_path)
        except Exception as _e:  # do not crash cycle
            if _log:
                _log.debug(
                    "monitors_summary skipped",
                    source="sequencer",
                    payload={"error": str(_e)},
                )

    # XCOM Check footer (channels • readiness • cooldown • table breach count)
    try:
        from .xcom_check_panel import render as _render_xcom_check  # type: ignore
        _render_xcom_check(dl, csum, default_json_path)
    except Exception as _e:  # do not crash cycle
        if _log:
            _log.debug("xcom_check_panel skipped", source="sequencer", payload={"error": str(_e)})
