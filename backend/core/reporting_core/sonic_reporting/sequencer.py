# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any

from .banner_config import render_banner
from .sync_cycle import render as render_sync
from .positions_debug import render as render_positions_debug
from .prices_table import render as render_prices_table  # your existing prices table renderer
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
    Clean, deterministic order:

      1) Sync Data
      2) Monitors header
      3) Positions Debug (provider/method/rows/status)
      4) 💰 Prices table (dashed header)
      5) Monitor Evaluations table
      6) Positions Snapshot table (headers+rows only; no extra title/dividers)

    No extra blank lines before table headers.
    """
    # 1) Sync Data
    write_line("---------------------- 🛠️ 🛠️ 🛠️  Sync  Data  🛠️ 🛠️ 🛠️ ----------------------")
    render_sync(dl, csum, default_json_path)

    # 3) Positions adapter debug
    render_positions_debug(dl, csum)

    # 4) Prices (match section style with dashed header)
    write_line("---------------------- 💰  Prices  ----------------------")
    render_prices_table(csum)


    write_line("---------------------- 🖥️ 🖥️ 🖥️  Monitors  🖥️ 🖥️ 🖥️ ----------------------")
    render_evals(dl, csum)

    write_line("---------------------- 💰  Positions  ----------------------")
    render_positions(dl, csum)
