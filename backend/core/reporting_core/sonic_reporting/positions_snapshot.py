from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime, timezone

# ──────────────────────────────────────────────────────────────────────────────
# Number parsing (handles '$', ',', '%', 'x', '×') so we can sum what we print
def _parse_num(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        for ch in ("$", ",", "%", "x", "X", "×"):
            s = s.replace(ch, "")
        s = s.replace("\u2013", "-")
        try:
            return float(s)
        except Exception:
            import re
            m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
            if m:
                try:
                    return float(m.group(0))
                except Exception:
                    return None
    return None

def _fmt_money(v: Optional[float]) -> str:
    return f"${v:,.2f}" if isinstance(v, (int, float, float)) else "-"

def _fmt_pct(v: Optional[float]) -> str:
    return f"{v:.2f}%" if isinstance(v, (int, float)) else "-"

def _fmt_lev(v: Optional[float]) -> str:
    return f"{v:.2f}×" if isinstance(v, (int, float)) else "-"

def _fmt_num(v: Optional[float]) -> str:
    return f"{v:.2f}" if isinstance(v, (int, float)) else "-"

def _fmt_asset(v: Any) -> str:
    if v is None:
        return "-"
    s = str(v).strip()
    return s or "-"

def _fmt_side(v: Any) -> str:
    s = str(v or "-").strip()
    return s.upper() or "-"

# ──────────────────────────────────────────────────────────────────────────────
# Locker access (tolerant)
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
    for k in keys:
        if isinstance(obj, dict) and k in obj:
            return obj[k]
        if hasattr(obj, k):
            return getattr(obj, k)
    return default

def _resolve_positions() -> List[Dict[str, Any]]:
    # 1) Preferred dl_positions.get_positions()
    if callable(dl_get_positions):
        try:
            data = dl_get_positions()
            if isinstance(data, list):
                return data
        except Exception:
            pass
    # 2) DataLocker fallback
    if DataLocker is not None:
        try:
            dl = DataLocker.get_instance() if hasattr(DataLocker, "get_instance") else DataLocker()  # type: ignore
            data = dl.get_positions()  # type: ignore[attr-defined]
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []

# ──────────────────────────────────────────────────────────────────────────────
# Travel% helper (only used if row lacks travel)
def _compute_travel_pct(side: str,
                        entry_price: Optional[float],
                        mark_price: Optional[float],
                        liq_price: Optional[float] = None) -> Optional[float]:
    # 0% at entry; >0 profitable; -100% at liquidation (long/short aware)
    if entry_price is None or mark_price is None:
        return None
    su = (side or "").upper()
    if su == "SHORT":
        pct = (entry_price - mark_price) / entry_price * 100.0
        if liq_price is not None and mark_price >= liq_price:
            return -100.0
    else:
        pct = (mark_price - entry_price) / entry_price * 100.0
        if liq_price is not None and mark_price <= liq_price:
            return -100.0
    return pct if pct >= -100.0 else -100.0

# Normalize one raw position row → console row dict
def _row_from_position(p: Any) -> Dict[str, Any]:
    asset = _get(p, "asset", "symbol", "name")
    side  = str(_get(p, "side", default="")).upper() or "LONG"

    value = _as_float(_get(p, "value", "notional", "size_usd"))
    pnl   = _as_float(_get(p, "pnl", "unrealized_pnl", "pnl_usd"))
    lev   = _as_float(_get(p, "lev", "leverage"))
    liq   = _as_float(_get(p, "liq", "liq_pct"))
    liqp  = _as_float(_get(p, "liq_price"))

    travel = _as_float(_get(p, "travel", "travel_pct"))
    if travel is None:
        entry = _as_float(_get(p, "entry", "entry_price"))
        mark  = _as_float(_get(p, "mark", "mark_price", "price"))
        travel = _compute_travel_pct(side, entry, mark, liqp)

    return {
        "asset": asset,
        "side": side,
        "value": value,
        "pnl": pnl,
        "lev": lev,
        "liq": liq,
        "travel": travel,
        # NOTE: if you want size-weighted strictly, ensure size is in the DL schema and populate it here.
        # This printer will gracefully fallback to |value| if size is missing per-row.
        "size": _as_float(_get(p, "size", "position_size", "qty", "amount")),
    }

# ──────────────────────────────────────────────────────────────────────────────
# Totals computation from the same cells we print (weight by Size, fallback |Value|)
def _extract_for_totals(row_cells: Sequence[str]) -> Dict[str, Optional[float]]:
    """
    row_cells must be the 7 visible cells in order:
      [Asset, Side, Value, PnL, Lev, Liq, Travel]
    """
    # We parse from the strings we printed.
    value  = _parse_num(row_cells[2])
    pnl    = _parse_num(row_cells[3])
    lev    = _parse_num(row_cells[4])
    travel = _parse_num(row_cells[6])
    return {"value": value, "pnl": pnl, "lev": lev, "travel": travel}

def _compute_footer_from_rows(rows_for_footer: List[List[str]],
                              sizes_if_any: Optional[List[Optional[float]]] = None) -> Dict[str, Optional[float]]:
    total_value = 0.0
    total_pnl = 0.0
    w_lev_num = w_lev_den = 0.0
    w_trv_num = w_trv_den = 0.0

    for i, rc in enumerate(rows_for_footer):
        f = _extract_for_totals(rc)
        v, p, l, t = f["value"], f["pnl"], f["lev"], f["travel"]
        if v is not None:
            total_value += v
        if p is not None:
            total_pnl += p

        w = None
        if sizes_if_any is not None:
            s = sizes_if_any[i]
            if isinstance(s, (int, float)):
                w = abs(float(s))
        if w is None and v is not None:
            w = abs(v)
        if w is not None:
            if l is not None:
                w_lev_num += w * l
                w_lev_den += w
            if t is not None:
                w_trv_num += w * t
                w_trv_den += w

    lev_w = (w_lev_num / w_lev_den) if w_lev_den > 0 else None
    trv_w = (w_trv_num / w_trv_den) if w_trv_den > 0 else None
    return {"value": total_value, "pnl": total_pnl,
            "avg_lev_weighted": lev_w, "avg_travel_weighted": trv_w}

# ──────────────────────────────────────────────────────────────────────────────
def _print_positions_table(rows: List[Dict[str, Any]]) -> None:
    """Print Positions and one totals row at the bottom."""
    WIDTHS = {"a": 5, "s": 6, "v": 10, "p": 10, "l": 7, "liq": 8, "t": 8}

    header = (
        f"{'Asset':<{WIDTHS['a']}} "
        f"{'Side':<{WIDTHS['s']}} "
        f"{'Value':>{WIDTHS['v']}} "
        f"{'PnL':>{WIDTHS['p']}} "
        f"{'Lev':>{WIDTHS['l']}} "
        f"{'Liq':>{WIDTHS['liq']}} "
        f"{'Travel':>{WIDTHS['t']}}"
    )
    print(header)

    rows_for_footer: List[List[str]] = []
    sizes_for_weight: List[Optional[float]] = []

    if not rows:
        line = (
            f"{'-':<{WIDTHS['a']}} "
            f"{'-':<{WIDTHS['s']}} "
            f"{'-':>{WIDTHS['v']}} "
            f"{'-':>{WIDTHS['p']}} "
            f"{'-':>{WIDTHS['l']}} "
            f"{'-':>{WIDTHS['liq']}} "
            f"{'-':>{WIDTHS['t']}}"
        )
        print(line)
    else:
        for r in rows:
            asset_str  = _fmt_asset(r.get("asset"))
            side_str   = _fmt_side(r.get("side"))
            value_str  = _fmt_money(r.get("value"))
            pnl_str    = _fmt_money(r.get("pnl"))
            lev_str    = _fmt_lev(r.get("lev"))
            liq_str    = _fmt_num(r.get("liq"))
            travel_str = _fmt_pct(r.get("travel"))

            line = (
                f"{asset_str:<{WIDTHS['a']}} "
                f"{side_str:<{WIDTHS['s']}} "
                f"{value_str:>{WIDTHS['v']}} "
                f"{pnl_str:>{WIDTHS['p']}} "
                f"{lev_str:>{WIDTHS['l']}} "
                f"{liq_str:>{WIDTHS['liq']}} "
                f"{travel_str:>{WIDTHS['t']}}"
            )
            print(line)

            rows_for_footer.append([asset_str, side_str, value_str, pnl_str, lev_str, liq_str, travel_str])
            sizes_for_weight.append(_as_float(r.get("size")))

    # Compute and print the totals row (Asset/Side/Liq blank)
    totals = _compute_footer_from_rows(rows_for_footer, sizes_for_weight)
    footer_line = (
        f"{'':<{WIDTHS['a']}} "
        f"{'':<{WIDTHS['s']}} "
        f"{_fmt_money(totals.get('value')):>{WIDTHS['v']}} "
        f"{_fmt_money(totals.get('pnl')):>{WIDTHS['p']}} "
        f"{_fmt_lev(totals.get('avg_lev_weighted')):>{WIDTHS['l']}} "
        f"{'':>{WIDTHS['liq']}} "
        f"{_fmt_pct(totals.get('avg_travel_weighted')):>{WIDTHS['t']}}"
    )
    # style the totals a bit
    CYAN = "\x1b[38;5;45m"; BOLD = "\x1b[1m"; RESET = "\x1b[0m"
    print(f"{CYAN}{BOLD}{footer_line}{RESET}")

# ──────────────────────────────────────────────────────────────────────────────
# Build snapshot (for API/web) — leaves UI rendering to _print_positions_table
def _snapshot_totals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_value = 0.0
    total_pnl = 0.0
    w_lev_num = w_lev_den = 0.0
    w_trv_num = w_trv_den = 0.0

    for r in rows:
        v = r.get("value")
        p = r.get("pnl")
        l = r.get("lev")
        t = r.get("travel")
        if isinstance(v, (int, float)):
            fv = float(v)
            total_value += fv
            if isinstance(l, (int, float)):
                w_lev_num += abs(fv) * float(l)
                w_lev_den += abs(fv)
            if isinstance(t, (int, float)):
                w_trv_num += abs(fv) * float(t)
                w_trv_den += abs(fv)
        if isinstance(p, (int, float)):
            total_pnl += float(p)

    return {
        "value": total_value,
        "pnl": total_pnl,
        "avg_lev_weighted": (w_lev_num / w_lev_den) if w_lev_den > 0 else None,
        "avg_travel_weighted": (w_trv_num / w_trv_den) if w_trv_den > 0 else None,
    }

# ──────────────────────────────────────────────────────────────────────────────
# Public API
def print_positions_snapshot() -> None:
    rows_raw = _resolve_positions()
    rows = [_row_from_position(p) for p in rows_raw]
    _print_positions_table(rows)

def build_positions_snapshot() -> Dict[str, Any]:
    rows_raw = _resolve_positions()
    rows = [_row_from_position(p) for p in rows_raw]
    return {
        "asof": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
        "totals": _snapshot_totals(rows),
    }
