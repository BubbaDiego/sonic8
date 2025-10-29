# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from .writer import write_table
from .styles import ICON_POS
from .data_access import read_positions

def _usd(v):
    try:
        return f"${float(v):.2f}".rstrip("0").rstrip(".")
    except Exception:
        return "—"

def _pct(v):
    try:
        return f"{float(v):.2f}%".rstrip("0").rstrip(".")
    except Exception:
        return "—"

def render(dl, csum: Dict[str, Any]) -> None:
    cycle_id = csum.get("cycle_id")
    data = read_positions(dl, cycle_id)
    title = ICON_POS + " Positions Snapshot"
    headers = ["Asset", "Side", "Value", "PnL", "Lev", "Liq", "Travel"]
    rows = []
    for r in data["rows"]:
        if isinstance(r, dict) or hasattr(r, "keys"):
            rows.append([
                str(r.get("asset") or r.get("asset_type") or "—"),
                str(r.get("side")  or r.get("position_type") or "—"),
                _usd(r.get("value_usd")),
                _usd(r.get("pnl_after_fees_usd")),
                f"{r.get('leverage','—')}×" if r.get("leverage") else "—",
                _pct(r.get("liquidation_distance")),
                _pct(r.get("travel_percent"))
            ])
        else:
            # tuple fallback indices
            asset, side, val, pnl, lev, liq, trav = (r + (None,)*7)[:7]
            rows.append([str(asset or "—"), str(side or "—"), _usd(val), _usd(pnl),
                         (f"{lev}×" if lev is not None else "—"), _pct(liq), _pct(trav)])
    write_table(title, headers, rows if rows else [["—","—","—","—","—","—","—"]])
