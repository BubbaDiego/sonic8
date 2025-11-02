from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


# Try the Data Locker entrypoints but never crash if they aren't present yet.
try:
    from backend.data.dl_positions import get_positions as dl_get_positions  # type: ignore
except Exception:  # pragma: no cover
    dl_get_positions = None  # type: ignore

try:
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:  # pragma: no cover
    DataLocker = None  # type: ignore


# ---------- helpers ----------

def _as_float(x: Any) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except Exception:
        return None


def _get(obj: Any, *keys: str, default: Any = None) -> Any:
    """
    Safe getter that works for dicts OR objects with attributes.
    Returns the first match or `default`.
    """
    for k in keys:
        if isinstance(obj, dict) and k in obj:
            return obj[k]
        if hasattr(obj, k):
            return getattr(obj, k)
    return default


def _resolve_positions() -> List[Dict[str, Any]]:
    """
    Pull positions from the Data Locker:
      1) Prefer dl_positions.get_positions()
      2) Fallback to DataLocker().get_positions() or DataLocker.get_instance().get_positions()
    Always return a list (possibly empty). Never raise.
    """
    # 1) Preferred dl_positions
    if callable(dl_get_positions):
        try:
            data = dl_get_positions()
            if isinstance(data, list):
                return data
        except Exception:
            pass

    # 2) DataLocker
    if DataLocker is not None:
        try:
            dl = DataLocker.get_instance() if hasattr(DataLocker, "get_instance") else DataLocker()  # type: ignore
            data = dl.get_positions()  # type: ignore[attr-defined]
            if isinstance(data, list):
                return data
        except Exception:
            pass

    return []


def _compute_travel_pct(
    side: str,
    entry_price: Optional[float],
    mark_price: Optional[float],
    liq_price: Optional[float] = None,
) -> Optional[float]:
    """
    Travel% (your definition):
      - 0% at entry
      - >0% when profitable
      - -100% at liquidation

    LONG  : (mark - entry) / entry * 100
    SHORT : (entry - mark) / entry * 100

    If liq_price is present and the mark has crossed the boundary, clamp to -100.
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
    Normalize a position record into a row both UIs can render.
    Prefer existing fields; compute travel only if not present.
    """
    asset = _get(p, "asset", "symbol", "name")
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
    }


def _totals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Totals:
      - Sum(value), Sum(pnl)
      - Weighted avg leverage by |value|
      - Weighted avg travel% by |value|
      - Long/Short splits (optional diagnostics)
    """
    total_value = 0.0
    total_pnl = 0.0

    w_lev_num = w_lev_den = 0.0
    w_trv_num = w_trv_den = 0.0

    long_val = 0.0
    short_val = 0.0

    for r in rows:
        v = r.get("value")
        pnl = r.get("pnl")
        lev = r.get("lev")
        trv = r.get("travel")

        if isinstance(v, (int, float)):
            fv = float(v)
            total_value += fv

            if isinstance(lev, (int, float)):
                w_lev_num += abs(fv) * float(lev)
                w_lev_den += abs(fv)

            if isinstance(trv, (int, float)):
                w_trv_num += abs(fv) * float(trv)
                w_trv_den += abs(fv)

            if (r.get("side") or "").upper() == "SHORT":
                short_val += fv
            else:
                long_val += fv

        if isinstance(pnl, (int, float)):
            total_pnl += float(pnl)

    avg_lev_weighted = (w_lev_num / w_lev_den) if w_lev_den > 0 else None
    avg_travel_weighted = (w_trv_num / w_trv_den) if w_trv_den > 0 else None

    return {
        "count": len(rows),
        "value": total_value,
        "pnl": total_pnl,
        "value_long": long_val,
        "value_short": short_val,
        "avg_lev_weighted": avg_lev_weighted,
        "avg_travel_weighted": avg_travel_weighted,
    }


# ---------- public API ----------

def build_positions_snapshot() -> Dict[str, Any]:
    """
    Return a unified payload for BOTH console and web:
      { "asof", "rows": [...], "totals": {...} }
    """
    raw = _resolve_positions()
    rows = [_row_from_position(p) for p in raw]
    return {
        "asof": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "totals": _totals(rows),
    }
