# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, Iterable, Optional

from .writer import write_table

# ─────────────────────────────────────────────────────────────
# format helpers
# ─────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────
# value derivation using your DataLocker.get_latest_price(asset)
# ─────────────────────────────────────────────────────────────
def _latest_price(dl, asset: str) -> Optional[float]:
    try:
        rec = dl.get_latest_price(asset)  # your DataLocker utility
        # returns dict with current_price (or previous) when available
        p = rec.get("current_price")
        return float(p) if p is not None else None
    except Exception:
        return None

def _derive_value_if_missing(dl, asset: str, size, value):
    """If 'value' is missing/None and we have size, compute abs(size) * price."""
    try:
        if value is None and size not in (None, "", "—"):
            price = _latest_price(dl, str(asset).upper())
            if price is not None:
                return abs(float(size)) * price
    except Exception:
        pass
    return value

def _derive_leverage_if_missing(value, collateral, lev):
    """If lev is None but value and collateral exist, approximate lev = value / collateral."""
    try:
        if (lev is None or lev == "—") and value not in (None, 0) and collateral not in (None, 0):
            return float(value) / float(collateral)
    except Exception:
        pass
    return lev

# ─────────────────────────────────────────────────────────────
# renderer (DB-first via DataLocker.DLPositionManager)
# ─────────────────────────────────────────────────────────────
def render(dl, csum: Dict[str, Any]) -> None:
    """
    Render the Positions Snapshot **directly from the DB** using your DLPositionManager.
    No title row, no spacer: headers + rows only.

    Sources:
      - dl.positions.get_all_positions()  (DLPositionManager → positions table)
      - dl.get_latest_price(asset) to compute Value fallback when missing
    """
    # Pull runtime rows from your DL manager (no snapshot dependency)
    rows_src = []
    try:
        if hasattr(dl, "positions") and hasattr(dl.positions, "get_all_positions"):
            rows_src = dl.positions.get_all_positions()  # list[PositionDB] or list[dict]
        elif hasattr(dl, "read_positions"):
            rows_src = dl.read_positions()
        else:
            rows_src = []
    except Exception:
        rows_src = []

    headers = ["Asset", "Side", "Value", "PnL", "Lev", "Liq", "Travel"]
    out_rows: list[list[str]] = []

    for p in _coerce_iter(rows_src):
        # accept both dict and PositionDB model (your DL layer returns PositionDB)  # :contentReference[oaicite:3]{index=3}
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

        # derive value / leverage when missing
        value = _derive_value_if_missing(dl, asset, size, value)
        lev   = _derive_leverage_if_missing(value, coll, lev)

        out_rows.append([
            str(asset or "—"),
            str(side or "—"),
            _usd(value),
            _usd(pnl),
            f"{float(lev):.2f}×".rstrip("0").rstrip(".×") + "×" if lev not in (None, "", "—") else "—",
            _pct(liq),
            _pct(trav),
        ])

    # No title row → pass None so the table starts directly with headers.
    write_table(None, headers, out_rows if out_rows else [["—","—","—","—","—","—","—"]])
