# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any

from .banner_config import render_banner
from .sync_cycle import render as render_sync
from .positions_debug import render as render_positions_debug
from .prices_table import render as render_prices_table  # ← your existing prices table
from .evaluations_table import render as render_evals
from .positions_snapshot import render as render_positions
from .writer import write_line


def render_startup_banner(dl, default_json_path: str) -> None:
    """
    Print the Sonic Monitor Configuration banner (LAN URLs, config mode, paths, DB).
    """
    render_banner(dl, default_json_path)


def render_cycle(dl, csum: Dict[str, Any], *, default_json_path: str) -> None:
    """
    Orchestrate one console cycle in a clean, deterministic order:

      1) Sync Data (JSON path/parse/schema/normalized/effective thresholds)
      2) Monitors header
      3) Positions Debug (provider/method/rows/status) — always visible
      4) Prices table (Current / Previous / Δ / Δ%)  ← before positions
      5) Monitor Evaluations table
      6) Positions Snapshot table (no extra title/dividers here)

    Notes:
      - No extra blank lines before the table headers.
      - All duplicate suppression (once-per-cycle) happens inside section modules if needed.
    """
    # 1) Sync Data block
    write_line("---------------------- 🛠️ 🛠️ 🛠️  Sync  Data  🛠️ 🛠️ 🛠️ ----------------------")
    render_sync(dl, csum, default_json_path)

    # 2) Monitors header
    write_line("---------------------- 🖥️ 🖥️ 🖥️  Monitors  🖥️ 🖥️ 🖥️ ----------------------")

    # 3) Positions adapter debug (always show)
    render_positions_debug(dl, csum)

    # 4) Prices table (your existing module)
    render_prices_table(csum)

    # 5) Monitor Evaluations table (print directly under the header; no spacer)
    render_evals(dl, csum)

    # 6) Positions Snapshot table (no divider/title here—renderer prints headers only)
    render_positions(dl, csum)
