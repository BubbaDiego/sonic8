# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any

from .banner_config import render_banner
from .sync_data import render as render_sync                    # table ONLY (no internal title/spacers)
from .prices_table import render as render_prices_table         # expects csum (table ONLY, no title/spacers)
from .evaluations_table import render as render_evals           # expects (dl, csum) (table ONLY)
from .positions_snapshot import render as render_positions      # expects (dl, csum) (table ONLY)
from .writer import write_line

def render_startup_banner(dl, default_json_path: str) -> None:
    """
    Print the Sonic Monitor Configuration banner (LAN URLs, config mode, paths, DB).
    Shown once at startup.
    """
    render_banner(dl, default_json_path)


def render_cycle(dl, csum: Dict[str, Any], *, default_json_path: str) -> None:
    """
    One full console cycle with sequencer-owned titles & spacing (Option A):

      1) Sync Data        (title here) + table (sync_data.render)
      2) Prices           (title here) + table (prices_table.render)
      3) Monitors         (title here) + table (evaluations_table.render)
      4) Positions        (title here) + table (positions_snapshot.render)

    Each renderer prints only its table (no internal dashed title or extra spacers).
    """

    # 1) Sync Data
    write_line("")  # single spacer from previous block
    write_line("---------------------- 🛠️  Sync  Data  🛠️ ----------------------")
    render_sync(dl, csum, default_json_path)

    # 2) Prices (expects: csum)
    write_line("")
    write_line("---------------------- 💰  Prices  ----------------------")
    render_prices_table(csum)

    # 3) Monitors (expects: dl, csum)
    write_line("")
    write_line("---------------------- 🖥️  Monitors  ----------------------")
    render_evals(dl, csum)

    # 4) Positions (expects: dl, csum)
    write_line("")
    write_line("---------------------- 📈  Positions  ----------------------")
    render_positions(dl, csum)
