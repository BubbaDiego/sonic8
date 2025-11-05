# -*- coding: utf-8 -*-
from __future__ import annotations
"""
positions_panel — classic version (pre-adaptive)
- Uses DataLocker.get_manager("positions")
- Calls manager.active() for rows
- Prints with the snapshot printer for aligned columns + totals
- Sequencer contract: render(dl, csum, default_json_path)
"""

from typing import Any, Mapping, List, Dict, Optional

# Reuse the snapshot printer for consistent layout
try:
    from backend.core.reporting_core.sonic_reporting.positions_snapshot import (
        _print_positions_table as _print_table
    )
except Exception:
    _print_table = None  # fallback handled below


# ------------ helpers ------------
def _as_dict(obj: Any) -> Mapping[str, Any]:
    if isinstance(obj, dict):
        return obj
    return getattr(obj, "__dict__", {}) or {}


def _normalize_row(p: Any) -> Dict[str, Any]:
    """
    Minimal normalization used by the classic panel.
    Assumes positions manager already returns the common fields.
    """
    row = _as_dict(p)

    # Basic, conservative extraction (classic aliases)
    asset = (
        row.get("asset")
        or row.get("symbol")
        or row.get("ticker")
        or row.get("coin")
        or row.get("name")
        or "---"
    )
    if isinstance(asset, str):
        asset = asset.upper()

    side = (
        row.get("side")
        or row.get("position")
        or row.get("dir")
        or row.get("direction")
        or "LONG"
    )
    side = str(side).upper()
    if side not in ("LONG", "SHORT"):
        side = "LONG"

    value = row.get("value") or row.get("value_usd") or row.get("size_usd") or row.get("notional") or row.get("notional_usd")
    pnl   = row.get("pnl") or row.get("pnl_usd") or row.get("unrealized_pnl") or row.get("profit") or row.get("pl")
    lev   = row.get("lev") or row.get("leverage") or row.get("x")
    liq   = row.get("liq") or row.get("liq_pct") or row.get("liquidation") or row.get("liquidation_distance_pct") or row.get("liq_dist")
    travel = row.get("travel") or row.get("travel_pct") or row.get("move_pct")

    # Coerce simple numerics to float when possible
    def _f(x: Any) -> Optional[float]:
        try:
            return float(x)
        except Exception:
            return None

    return {
        "asset": asset or "---",
        "side": side,
        "value": _f(value),
        "pnl": _f(pnl),
        "lev": _f(lev),
        "liq": _f(liq),
        "travel": _f(travel),
    }


# ------------ core ------------
def _rows_from_dl_positions_manager(dl: Any) -> List[Mapping[str, Any]]:
    """
    Classic path: dl.get_manager('positions').active()
    Returns [] if anything is missing or raises.
    """
    try:
        get_manager = getattr(dl, "get_manager", None)
        if not callable(get_manager):
            return []
        mgr = get_manager("positions")
        if not mgr:
            return []
        active = getattr(mgr, "active", None)
        if not callable(active):
            return []
        rows = active() or []
        return [_as_dict(r) for r in rows]
    except Exception:
        return []


def _print_minimal(rows: List[Dict[str, Any]]) -> None:
    # Simple fallback table (classic)
    print("Asset Side        Value        PnL     Lev      Liq   Travel")
    if not rows:
        print("-     -               -          -       -        -        -")
        print("\n                  $0.00      $0.00       -                 -")
        return

    total_value = 0.0
    total_pnl = 0.0

    for r in rows:
        asset = f"{(r.get('asset') or '---'):<5}"
        side  = f"{(r.get('side') or 'LONG'):<5}"
        v = r.get("value") or 0.0
        p = r.get("pnl") or 0.0
        total_value += v
        total_pnl += p
        val   = f"{v:>10,.2f}"
        pnl   = f"{p:>10,.2f}"
        lev   = "" if r.get("lev") is None else f"{r['lev']:.2f}"
        liq   = "" if r.get("liq") is None else f"{r['liq']:.2f}%"
        trav  = "" if r.get("travel") is None else f"{r['travel']:.2f}%"
        print(f"{asset} {side} {val:>10} {pnl:>10} {lev:>7} {liq:>7} {trav:>7}")

    print(f"\n{'':18}${total_value:,.2f}  ${total_pnl:,.2f}       -                 -")


def _render_core(dl: Any) -> None:
    rows_raw = _rows_from_dl_positions_manager(dl)
    rows = [_normalize_row(p) for p in rows_raw]

    if _print_table is not None:
        _print_table(rows)
    else:
        _print_minimal(rows)

    print(f"\n[POSITIONS] dl:get_manager.active ({len(rows) if rows else 0} rows)")


# ------------ public API ------------
def print_positions_panel(dl=None) -> None:
    # Classic path expects the sequencer to pass `dl`
    if dl is None:
        # If not provided, we simply render nothing safely
        _print_minimal([])
        print("\n[POSITIONS] dl:none (0 rows)")
        return
    _render_core(dl)


# Sequencer contract: render(dl, csum, default_json_path)
def render(dl=None, csum=None, default_json_path=None, **_):
    print_positions_panel(dl=dl)
