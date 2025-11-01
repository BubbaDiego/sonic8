from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

# Prefer Locker helpers if available; guard so this file never blocks startup.
try:
    from backend.data.dl_positions import get_positions as dl_get_positions  # type: ignore
except Exception:
    dl_get_positions = None

try:
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:
    DataLocker = None  # type: ignore


def _as_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _get(obj: Any, *keys: str, default: Any = None) -> Any:
    """Safe getter for dicts / models."""
    for k in keys:
        if isinstance(obj, dict):
            if k in obj:
                return obj[k]
        else:
            if hasattr(obj, k):
                return getattr(obj, k)
    return default


def _resolve_positions() -> List[Dict[str, Any]]:
    """
    Pull positions from the Data Locker:
      - Prefer dl_positions.get_positions()
      - Fallback to DataLocker().get_positions()
      - Return a list of dict-like objects
    """
    if callable(dl_get_positions):
        try:
            data = dl_get_positions()
            if isinstance(data, list):
                return data
        except Exception:
            pass
    if DataLocker is not None:
        try:
            dl = DataLocker()
            data = dl.get_positions()  # type: ignore[attr-defined]
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def _compute_travel_pct(side: str,
                        entry_price: Optional[float],
                        mark_price: Optional[float],
                        liq_price: Optional[float] = None) -> Optional[float]:
    """
    Travel% (your standard):
      - 0%  at entry
      - >0% when profitable
      - -100% at liquidation
    LONG : (mark - entry) / entry * 100
    SHORT: (entry - mark) / entry * 100
    If liq_price is provided and price crosses the liq boundary, clamp to -100.
    """
    if entry_price is None or mark_price is None:
        return None

    side_u = (side or "").upper()
    if side_u == "SHORT":
        pct = (entry_price - mark_price) / entry_price * 100.0
        if liq_price is not None and mark_price >= liq_price:
            return -100.0
    else:
        pct = (mark_price - entry_price) / entry_price * 100.0
        if liq_price is not None and mark_price <= liq_price:
            return -100.0

    return pct if pct >= -100.0 else -100.0


def _row_from_position(p: Any) -> Dict[str, Any]:
    """
    Normalize a position into the row contract required by both UIs.
    Prefer precomputed fields from the Data Locker; compute Travel% only if missing.
    """
    asset = _get(p, "asset", "symbol", "name", default=None)
    side = str(_get(p, "side", default="")).upper() or "LONG"

    value = _as_float(_get(p, "value", "notional", "size_usd"))
    pnl = _as_float(_get(p, "pnl", "unrealized_pnl", "pnl_usd"))
    lev = _as_float(_get(p, "lev", "leverage"))

    liq_pct = _as_float(_get(p, "liq", "liq_pct"))
    liq_price = _as_float(_get(p, "liq_price"))

    travel = _as_float(_get(p, "travel", "travel_pct"))
    if travel is None:
        entry = _as_float(_get(p, "entry", "entry_price"))
        mark = _as_float(_get(p, "mark", "mark_price", "price"))
        travel = _compute_travel_pct(side, entry, mark, liq_price)

    return {
        "asset": asset,
        "side": side,
        "value": value,
        "pnl": pnl,
        "lev": lev,
        "liq": liq_pct,
        "travel": travel,
        # raw inputs in case you want to debug downstream
        "_entry": _as_float(_get(p, "entry", "entry_price")),
        "_mark": _as_float(_get(p, "mark", "mark_price", "price")),
        "_liq_price": liq_price,
    }


def _totals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Footer totals:
      - Sum(value), Sum(pnl)
      - Weighted avg leverage by |value|
      - Weighted avg travel% by |value|   (NEW)
      - Split long/short exposure for clarity
    """
    total_value = 0.0
    total_pnl = 0.0

    w_lev_num = 0.0
    w_lev_den = 0.0

    w_trv_num = 0.0
    w_trv_den = 0.0

    long_val = 0.0
    short_val = 0.0

    for r in rows:
        v = _as_float(r.get("value"))
        pnl = _as_float(r.get("pnl"))
        lev = _as_float(r.get("lev"))
        trv = _as_float(r.get("travel"))

        if isinstance(v, float):
            total_value += v

            if isinstance(lev, float):
                w_lev_num += abs(v) * lev
                w_lev_den += abs(v)

            if isinstance(trv, float):
                w_trv_num += abs(v) * trv
                w_trv_den += abs(v)

            if (r.get("side") or "").upper() == "SHORT":
                short_val += v
            else:
                long_val += v

        if isinstance(pnl, float):
            total_pnl += pnl

    avg_lev_weighted = (w_lev_num / w_lev_den) if w_lev_den > 0 else None
    avg_travel_weighted = (w_trv_num / w_trv_den) if w_trv_den > 0 else None

    return {
        "count": len(rows),
        "value": total_value,
        "pnl": total_pnl,
        "value_long": long_val,
        "value_short": short_val,
        "avg_lev_weighted": avg_lev_weighted,
        "avg_travel_weighted": avg_travel_weighted,  # NEW
    }


def build_positions_snapshot() -> Dict[str, Any]:
    """
    Public entrypoint for BOTH the Sonic Monitor and the Dashboard.
    Returns: { "asof": iso8601, "rows": [...], "totals": {...} }
    """
    raw_positions = _resolve_positions()
    rows = [_row_from_position(p) for p in raw_positions]
    return {
        "asof": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "totals": _totals(rows),
    }
