# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Iterable, Optional

from .writer import write_table, HAS_RICH

ICON_BY_ASSET = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}

HDR_BLUE = "\x1b[94m"
RESET = "\x1b[0m"


# ---------- format helpers ----------
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

def _coerce_iter(x: Any) -> Iterable:
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return x
    try:
        iter(x)  # type: ignore
        return x  # type: ignore
    except Exception:
        return [x]


# ---------- derivations (used only when fields are missing) ----------
def _latest_price(dl, asset: str) -> Optional[float]:
    try:
        data = dl.get_latest_price(asset)  # your DataLocker helper
        p = data.get("current_price")
        return float(p) if p is not None else None
    except Exception:
        return None

def _derive_value(dl, asset, size, value):
    if value is None and size not in (None, "", "—"):
        try:
            price = _latest_price(dl, str(asset).upper())
            if price is not None:
                return abs(float(size)) * price
        except Exception:
            pass
    return value

def _derive_lev(value, collateral, lev):
    try:
        if (lev is None or lev == "—") and value not in (None, 0) and collateral not in (None, 0):
            return float(value) / float(collateral)
    except Exception:
        pass
    return lev


# ---------- renderer (DB-first via DataLocker.DLPositionManager) ----------
def render(dl, csum: Dict[str, Any]) -> None:
    """
    Render the Positions Snapshot directly from DLPositionManager / DataLocker.
    No title, no spacer: headers + rows only.
    """
    # 1) fetch rows from DB through your DataLocker/DLPositionManager
    rows_src = []
    try:
        if hasattr(dl, "positions") and hasattr(dl.positions, "get_all_positions"):
            rows_src = dl.positions.get_all_positions()  # list[PositionDB] or list[dict]
        elif hasattr(dl, "read_positions"):
            rows_src = dl.read_positions()
    except Exception:
        rows_src = []

    headers = ["Asset", "Side", "Value", "PnL", "Lev", "Liq", "Travel"]
    render_headers = [f"{HDR_BLUE}{h}{RESET}" for h in headers] if not HAS_RICH else headers
    out_rows: list[list[str]] = []

    for p in _coerce_iter(rows_src):
        if isinstance(p, dict) or hasattr(p, "keys"):
            g = p.get  # type: ignore[attr-defined]
            asset = g("asset_type") or g("asset") or g("symbol") or "—"
            side  = g("position_type") or g("side") or g("dir") or "—"
            size  = g("size") or g("size_usd")
            value = g("value") or g("value_usd") or g("position_value_usd")
            pnl   = g("pnl_after_fees_usd") or g("pnl_usd") or g("pnl")
            lev   = g("leverage") or g("lev")
            liq   = g("liquidation_distance") or g("liq_dist") or g("liq_percent")
            trav  = g("travel_percent") or g("movement_percent") or g("travel")
            coll  = g("collateral")
        else:
            asset = getattr(p, "asset_type", None) or getattr(p, "asset", None) or getattr(p, "symbol", None) or "—"
            side  = getattr(p, "position_type", None) or getattr(p, "side", None) or getattr(p, "dir", None) or "—"
            size  = getattr(p, "size", None) or getattr(p, "size_usd", None)
            value = getattr(p, "value", None) or getattr(p, "value_usd", None) or getattr(p, "position_value_usd", None)
            pnl   = getattr(p, "pnl_after_fees_usd", None) or getattr(p, "pnl_usd", None) or getattr(p, "pnl", None)
            lev   = getattr(p, "leverage", None) or getattr(p, "lev", None)
            liq   = getattr(p, "liquidation_distance", None) or getattr(p, "liq_dist", None) or getattr(p, "liq_percent", None)
            trav  = getattr(p, "travel_percent", None) or getattr(p, "movement_percent", None) or getattr(p, "travel", None)
            coll  = getattr(p, "collateral", None)

        # derive missing values
        value = _derive_value(dl, asset, size, value)
        lev   = _derive_lev(value, coll, lev)

        sym = str(asset or "—").upper()
        icon = ICON_BY_ASSET.get(sym, "◻️")
        out_rows.append([
            f"{icon} {sym}",
            str(side or "—"),
            _usd(value),
            _usd(pnl),
            f"{float(lev):.2f}×".rstrip("0").rstrip(".×") + "×" if lev not in (None, "", "—") else "—",
            _pct(liq),
            _pct(trav),
        ])

    # No title row → pass None; writer prints only headers + rows.
    write_table(None, render_headers, out_rows if out_rows else [["—","—","—","—","—","—","—"]])
