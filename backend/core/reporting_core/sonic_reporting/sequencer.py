# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any

from .banner_config import render_banner
from .sync_cycle import render as render_sync
from .prices_table import render as render_prices_table      # table ONLY (no internal title)
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
    Console sequence (no extra blank lines; titles consistent):

      1) Sync Data (dashed header)
      2) 💰 Prices (dashed header) + prices_table
      3) 🖥️ Monitors (dashed header) + Evaluations table
      4) 📈 Positions (dashed header) + Positions Snapshot (headers+rows only)

    Notes:
      - prices_table must NOT print its own title (sequencer provides the dashed header).
      - positions_snapshot must render only headers+rows (no internal title/spacer).
      - We intentionally do NOT print the old “Positions Debug …” line.
    """
    # 1) Sync Data
    write_line("---------------------- 🛠️ 🛠️ 🛠️  Sync  Data  🛠️ 🛠️ 🛠️ ----------------------")
    render_sync(dl, csum, default_json_path)

    # 2) Prices
    write_line("---------------------- 💰 💰 💰  Prices  💰 💰 💰 ----------------------")
    render_prices_table(csum)

    # 3) Monitors + Evaluations
    write_line("---------------------- 🖥️ 🖥️ 🖥️  Monitors  🖥️ 🖥️ 🖥️ ----------------------")
    render_evals(dl, csum)

    # 4) Positions Snapshot
    write_line("---------------------- 📈 📈 📈  Positions 📈 📈 📈 ----------------------")
    render_positions(dl, csum)
