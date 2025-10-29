# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List
from .writer import write_table
from .styles import ICON_POS
# NOTE:
#   Importing the adapter has been flaky on some deployments where the
#   helper is missing (older builds / partial installs).  We make the import
#   defensive so the UI still renders using the other data sources.
try:  # pragma: no cover - import-time guard only
    from .positions_core_adapter import get_positions_from_core as _get_positions_from_core
except ImportError:  # pragma: no cover - adapter unavailable
    _get_positions_from_core = None
from .data_access import read_positions_db

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

def _as_kv_dict(x: Any):
    try:
        if isinstance(x, (list, tuple)) and x and all(
            isinstance(t, (list, tuple)) and len(t) == 2 and isinstance(t[0], (str, bytes))
            for t in x
        ):
            return {str(k): v for k, v in x}
    except Exception:
        pass
    return None

def _normalize_row(r: Any) -> Dict[str, Any]:
    """Normalize a single row from any feed (core/summary/db), including kv-pair lists."""
    as_kv = _as_kv_dict(r)
    if as_kv is not None:
        r = as_kv

    if isinstance(r, dict) or hasattr(r, "keys"):
        asset = r.get("asset") or r.get("asset_type") or r.get("symbol")
        side  = r.get("side")  or r.get("position_type") or r.get("dir")
        val   = r.get("size_usd") or r.get("value_usd") or r.get("position_value_usd") or r.get("value")
        pnl   = r.get("pnl_after_fees_usd") or r.get("pnl_usd") or r.get("pnl")
        lev   = r.get("leverage") or r.get("lev") or r.get("leverage_x")
        liq   = r.get("liq_dist") or r.get("liquidation_distance") or r.get("liq_percent") or r.get("liq_distance")
        trav  = r.get("travel_percent") or r.get("movement_percent") or r.get("travel")
        return {
            "asset": asset, "side": side,
            "value_usd": val, "pnl_after_fees_usd": pnl,
            "leverage": lev, "liquidation_distance": liq, "travel_percent": trav
        }

    try:
        asset, side, val, pnl, lev, liq, trav = (list(r) + [None]*7)[:7]
    except Exception:
        asset = side = val = pnl = lev = liq = trav = None
    return {
        "asset": asset, "side": side,
        "value_usd": val, "pnl_after_fees_usd": pnl,
        "leverage": lev, "liquidation_distance": liq, "travel_percent": trav
    }

def render(dl, csum: Dict[str, Any]) -> None:
    cycle_id = csum.get("cycle_id")

    # A) Positions Core feed (same source as the web UI)
    if _get_positions_from_core is not None:
        rows = _get_positions_from_core(cycle_id) or []
    else:
        rows = []

    # B) Summary feed
    if not rows and isinstance(csum, dict):
        raw = (csum.get("positions") or {}).get("rows") or []
        if raw:
            rows = [_normalize_row(r) for r in raw]

    # C) DB fallback (runtime/snapshot tables)
    if not rows:
        rows = [ _normalize_row(r) for r in (read_positions_db(dl, cycle_id).get("rows") or []) ]

    title = ICON_POS + " Positions Snapshot"
    headers = ["Asset", "Side", "Value", "PnL", "Lev", "Liq", "Travel"]

    def _row(r: Dict[str, Any]):
        # Only append “×” when leverage is numeric-ish
        lev = r.get("leverage")
        lev_txt = "—"
        try:
            if lev is not None and str(lev).strip() != "":
                f = float(lev)
                lev_txt = f"{f:.2f}".rstrip("0").rstrip(".") + "×"
        except Exception:
            lev_txt = "—"
        return [
            str(r.get("asset") or "—"),
            str(r.get("side") or "—"),
            _usd(r.get("value_usd")),
            _usd(r.get("pnl_after_fees_usd")),
            lev_txt,
            _pct(r.get("liquidation_distance")),
            _pct(r.get("travel_percent")),
        ]

    body = [_row(r) for r in rows]
    write_table(title, headers, body if body else [["—","—","—","—","—","—","—"]])
