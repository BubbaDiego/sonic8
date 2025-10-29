# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
import importlib

def _as_kv_dict(x: Any) -> Optional[Dict[str, Any]]:
    """
    If x looks like a list/tuple of (key, value) pairs (e.g., dict.items()),
    convert it to a dict. Otherwise return None.
    """
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
    """Normalize a single row coming from positions core (robust to weird formats)."""
    # 1) If r is KV-pairs (e.g., list(dict.items())), convert first.
    as_kv = _as_kv_dict(r)
    if as_kv is not None:
        r = as_kv

    # 2) Dict-ish path
    if isinstance(r, dict) or hasattr(r, "keys"):
        asset = r.get("asset") or r.get("asset_type") or r.get("symbol")
        side  = r.get("side")  or r.get("position_type") or r.get("dir")
        val   = r.get("size_usd") or r.get("value_usd") or r.get("position_value_usd") or r.get("value")
        pnl   = r.get("pnl_after_fees_usd") or r.get("pnl_usd") or r.get("pnl")
        lev   = r.get("leverage") or r.get("lev") or r.get("leverage_x")
        liq   = r.get("liq_dist") or r.get("liquidation_distance") or r.get("liq_percent") or r.get("liq_distance")
        trav  = r.get("travel_percent") or r.get("movement_percent") or r.get("travel")
        ts    = r.get("ts") or r.get("timestamp") or r.get("time")
        return {
            "asset": asset, "side": side,
            "value_usd": val, "pnl_after_fees_usd": pnl,
            "leverage": lev, "liquidation_distance": liq,
            "travel_percent": trav, "ts": ts
        }

    # 3) Tuple/list fallback guess (asset, side, value, pnl, lev, liq, travel, ts)
    try:
        asset, side, val, pnl, lev, liq, trav, ts = (list(r) + [None]*8)[:8]
    except Exception:
        asset = side = val = pnl = lev = liq = trav = ts = None
    return {
        "asset": asset, "side": side,
        "value_usd": val, "pnl_after_fees_usd": pnl,
        "leverage": lev, "liquidation_distance": liq,
        "travel_percent": trav, "ts": ts
    }

def _try_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None

def get_positions_from_core(cycle_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Try a few likely entry points in Positions Core and return normalized rows.
    """
    candidates = [
        ("backend.core.positions_core", "get_console_rows"),
        ("backend.core.positions_core", "get_snapshot_rows"),
        ("backend.core.positions_core.service", "get_console_rows"),
        ("backend.core.positions_core.service", "get_snapshot_rows"),
        ("positions_core", "get_console_rows"),
        ("positions_core", "get_snapshot_rows"),
    ]
    for mod_name, attr in candidates:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, attr, None)
            if not callable(fn):
                continue
            if "cycle_id" in getattr(fn, "__code__", {}).__dict__.get("co_varnames", ()):
                rows = _try_call(fn, cycle_id=cycle_id)
            else:
                rows = _try_call(fn)
            if not rows:
                continue
            # If the core returns an iterable of kv-pair lists, normalize each
            normd = []
            for row in rows:
                as_kv = _as_kv_dict(row)
                normd.append(_normalize_row(as_kv if as_kv is not None else row))
            return normd
        except Exception:
            continue
    return None
