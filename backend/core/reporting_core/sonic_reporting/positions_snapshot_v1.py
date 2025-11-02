from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
        return float(x) if x is not None else None
    except Exception:
        return None


def _get(obj: Any, *keys: str, default: Any = None) -> Any:
    cur = obj
    for k in keys:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(k, default)
        else:
            cur = getattr(cur, k, default)
    return cur if cur is not None else default


def _resolve_positions() -> List[Dict[str, Any]]:
    if callable(dl_get_positions):
        try:
            data = dl_get_positions()
            if isinstance(data, list):
                return data
        except Exception:
            pass
    if DataLocker is not None:
        try:
            dl = (
                DataLocker.get_instance()  # type: ignore[attr-defined]
                if hasattr(DataLocker, "get_instance")
                else DataLocker()  # type: ignore[call-arg]
            )
            data = dl.get_positions()  # type: ignore[attr-defined]
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def _compute_travel_pct(
    side: str,
    entry: Optional[float],
    mark: Optional[float],
    liq_price: Optional[float],
) -> Optional[float]:
    """
    Travel% (rule of thumb):
      LONG  -> (mark - entry)/entry*100
      SHORT -> (entry - mark)/entry*100
      clamp to -100% if mark has crossed liq.
    """
    if entry is None or mark is None:
        return None
    su = (side or "").upper()
    if su == "SHORT":
        pct = (entry - mark) / entry * 100.0
        if liq_price is not None and mark >= liq_price:
            return -100.0
    else:
        pct = (mark - entry) / entry * 100.0
        if liq_price is not None and mark <= liq_price:
            return -100.0
    return pct if pct >= -100.0 else -100.0


def _row_from_position(p: Any) -> Dict[str, Any]:
    asset = _get(p, "asset", "symbol", "name")
    side = str(_get(p, "side", default="")).upper() or "LONG"
    value = _as_float(_get(p, "value", "notional", "size_usd"))
    pnl = _as_float(_get(p, "pnl", "unrealized_pnl", "pnl_usd"))
    lev = _as_float(_get(p, "lev", "leverage"))
    liq = _as_float(_get(p, "liq", "liq_pct"))
    liqp = _as_float(_get(p, "liq_price"))
    trav = _as_float(_get(p, "travel", "travel_pct"))
    if trav is None:
        entry = _as_float(_get(p, "entry", "entry_price"))
        mark = _as_float(_get(p, "mark", "mark_price", "price"))
        trav = _compute_travel_pct(side, entry, mark, liqp)
    return {
        "asset": asset,
        "side": side,
        "value": value,
        "pnl": pnl,
        "lev": lev,
        "liq": liq,
        "travel": trav,
    }


def _totals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    tot_val = 0.0
    tot_pnl = 0.0
    lev_num = lev_den = 0.0
    trv_num = trv_den = 0.0
    long_v = short_v = 0.0
    for r in rows:
        v = r.get("value")
        p = r.get("pnl")
        l = r.get("lev")
        t = r.get("travel")
        if isinstance(v, (int, float)):
            fv = float(v)
            tot_val += fv
            if isinstance(l, (int, float)):
                lev_num += abs(fv) * float(l)
                lev_den += abs(fv)
            if isinstance(t, (int, float)):
                trv_num += abs(fv) * float(t)
                trv_den += abs(fv)
            if (r.get("side") or "").upper() == "SHORT":
                short_v += fv
            else:
                long_v += fv
        if isinstance(p, (int, float)):
            tot_pnl += float(p)
    lev_w = (lev_num / lev_den) if lev_den > 0 else None
    trv_w = (trv_num / trv_den) if trv_den > 0 else None
    return {
        "count": len(rows),
        "value": tot_val,
        "pnl": tot_pnl,
        "value_long": long_v,
        "value_short": short_v,
        "avg_lev_weighted": lev_w,
        "avg_travel_weighted": trv_w,
    }


def build_positions_snapshot() -> Dict[str, Any]:
    rows = [_row_from_position(p) for p in _resolve_positions()]
    return {
        "asof": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "totals": _totals(rows),
    }
