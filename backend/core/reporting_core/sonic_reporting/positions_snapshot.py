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
            asset = r.get("asset") or r.get("asset_type") or r.get("symbol") or "—"
            side  = r.get("side") or r.get("position_type") or r.get("dir") or "—"
            val   = (
                r.get("size_usd")
                or r.get("value_usd")
                or r.get("position_value_usd")
                or r.get("value")
            )
            pnl   = r.get("pnl_after_fees_usd") or r.get("pnl_usd") or r.get("pnl")
            lev   = r.get("leverage") or r.get("lev") or r.get("leverage_x")
            liq   = (
                r.get("liq_dist")
                or r.get("liquidation_distance")
                or r.get("liq_percent")
                or r.get("liq_distance")
            )
            trav  = (
                r.get("travel_percent")
                or r.get("movement_percent")
                or r.get("travel")
            )
            rows.append([str(asset), str(side), _usd(val), _usd(pnl),
                         (f"{lev}×" if lev is not None else "—"), _pct(liq), _pct(trav)])
        else:
            # tuple fallback indices
            asset, side, val, pnl, lev, liq, trav = (r + (None,)*7)[:7]
            rows.append([str(asset or "—"), str(side or "—"), _usd(val), _usd(pnl),
                         (f"{lev}×" if lev is not None else "—"), _pct(liq), _pct(trav)])
    write_table(title, headers, rows if rows else [["—","—","—","—","—","—","—"]])
