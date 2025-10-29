# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from .banner_config import render_banner
from .sync_cycle import render as render_sync
from .evaluations_table import render as render_evals
from .positions_snapshot import render as render_positions
from .prices_tape import render as render_prices
from .writer import write_line


def render_startup_banner(dl, default_json_path: str) -> None:
    render_banner(dl, default_json_path)


def render_cycle(dl, csum: Dict[str, Any], *, default_json_path: str) -> None:
    # Sync block
    write_line("---------------------- 🛠️ 🛠️ 🛠️  Sync  Data  🛠️ 🛠️ 🛠️ ----------------------")
    render_sync(dl, csum, default_json_path)

    # Monitors + Evaluations (no spacer between divider and headers)
    write_line("---------------------- 🖥️ 🖥️ 🖥️  Monitors  🖥️ 🖥️ 🖥️ ----------------------")
    render_evals(dl, csum)

    # Positions Snapshot
    write_line("---------------------- 📊  Positions  Snapshot ----------------------")
    render_positions(dl, csum)

    # Prices line (single source of truth; footer is suppressed)
    render_prices(csum)
