from __future__ import annotations

from datetime import datetime, timezone


# ── Positions footer helpers (totals under table) ─────────────────────────────
from typing import Any, Dict, List, Optional, Sequence


def _ps_num(x: Any) -> Optional[float]:
    """Parse UI strings like '$1,234.56', '12.3%', '10.5x', '9.90×' into floats."""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        for ch in ("$", ",", "%", "x", "X", "×"):
            s = s.replace(ch, "")
        s = s.replace("\u2013", "-")  # en-dash → minus
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


def _ps_extract_row(row: Any) -> Dict[str, Optional[float]]:
    """
    Accepts either:
      • dict rows with keys (case-insensitive): value, pnl, size (optional), lev, travel
      • list/tuple rows (7 or 8 cells):
          7-col: [Asset, Side, Value, PnL, Lev, Liq, Travel]
          8-col: [Asset, Side, Value, PnL, Size, Lev, Liq, Travel]
    """

    if isinstance(row, dict):

        def get_ci(d: Dict[str, Any], key: str) -> Any:
            lk = key.lower()
            for k, v in d.items():
                if isinstance(k, str) and k.lower() == lk:
                    return v
            return None

        size = (
            _ps_num(get_ci(row, "size"))
            or _ps_num(get_ci(row, "qty"))
            or _ps_num(get_ci(row, "amount"))
            or _ps_num(get_ci(row, "position_size"))
        )
        return {
            "value": _ps_num(get_ci(row, "value")),
            "pnl": _ps_num(get_ci(row, "pnl")),
            "size": size,
            "lev": _ps_num(get_ci(row, "lev")),
            "travel": _ps_num(get_ci(row, "travel")),
        }

    if isinstance(row, Sequence):
        # 8 columns (with Size)
        if len(row) >= 8:
            # [Asset, Side, Value, PnL, Size, Lev, Liq, Travel]
            return {
                "value": _ps_num(row[2]),
                "pnl": _ps_num(row[3]),
                "size": _ps_num(row[4]),
                "lev": _ps_num(row[5]),
                "travel": _ps_num(row[7]),
            }
        # 7 columns (no Size)
        if len(row) >= 7:
            # [Asset, Side, Value, PnL, Lev, Liq, Travel]
            return {
                "value": _ps_num(row[2]),
                "pnl": _ps_num(row[3]),
                "size": None,  # we’ll fallback to |value| for weight
                "lev": _ps_num(row[4]),
                "travel": _ps_num(row[6]),
            }

    return {"value": None, "pnl": None, "size": None, "lev": None, "travel": None}


def _ps_compute_totals(rows: List[Any]) -> Dict[str, Optional[float]]:
    """
    Returns:
      {
        "value": ΣValue,
        "pnl": ΣPnL,
        "avg_lev_weighted": weighted average Lev,
        "avg_travel_weighted": weighted average Travel
      }
    Weights: prefer 'size' if present; otherwise use |value|.
    """

    total_value = 0.0
    total_pnl = 0.0
    w_lev_num = w_lev_den = 0.0
    w_trv_num = w_trv_den = 0.0

    for r in rows:
        f = _ps_extract_row(r)
        v, p, s, l, t = f["value"], f["pnl"], f["size"], f["lev"], f["travel"]

        if v is not None:
            total_value += v
        if p is not None:
            total_pnl += p

        weight = abs(s) if s is not None else (abs(v) if v is not None else None)
        if weight is not None:
            if l is not None:
                w_lev_num += weight * l
                w_lev_den += weight
            if t is not None:
                w_trv_num += weight * t
                w_trv_den += weight

    lev_w = (w_lev_num / w_lev_den) if w_lev_den > 0 else None
    trv_w = (w_trv_num / w_trv_den) if w_trv_den > 0 else None

    return {
        "value": total_value,
        "pnl": total_pnl,
        "avg_lev_weighted": lev_w,
        "avg_travel_weighted": trv_w,
    }


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


def _fmt_money(v: Optional[float]) -> str:
    return f"${float(v):,.2f}" if isinstance(v, (int, float)) else "-"


def _fmt_pct(v: Optional[float]) -> str:
    return f"{float(v):.2f}%" if isinstance(v, (int, float)) else "-"


def _fmt_lev(v: Optional[float]) -> str:
    return f"{float(v):.2f}×" if isinstance(v, (int, float)) else "-"


def _fmt_num(v: Optional[float]) -> str:
    return f"{float(v):.2f}" if isinstance(v, (int, float)) else "-"


def _fmt_asset(v: Any) -> str:
    if v is None:
        return "-"
    s = str(v).strip()
    return s or "-"


def _fmt_side(v: Any) -> str:
    s = str(v or "-").strip()
    return s.upper() or "-"


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


def _print_positions_table(rows: List[Dict[str, Any]]) -> None:
    """Print the Positions table with a totals footer."""

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

    # Collect the exact cells we print (so the footer mirrors the UI)
    _rows_for_footer: List[List[str]] = []

    if not rows:
        empty_line = (
            f"{'-':<{WIDTHS['a']}} "
            f"{'-':<{WIDTHS['s']}} "
            f"{'-':>{WIDTHS['v']}} "
            f"{'-':>{WIDTHS['p']}} "
            f"{'-':>{WIDTHS['l']}} "
            f"{'-':>{WIDTHS['liq']}} "
            f"{'-':>{WIDTHS['t']}}"
        )
        print(empty_line)
    else:
        for row in rows:
            asset_str = _fmt_asset(row.get("asset"))
            side_str = _fmt_side(row.get("side"))
            value_str = _fmt_money(row.get("value"))
            pnl_str = _fmt_money(row.get("pnl"))
            lev_str = _fmt_lev(row.get("lev"))
            liq_str = _fmt_num(row.get("liq"))
            travel_str = _fmt_pct(row.get("travel"))

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

            _rows_for_footer.append([
                asset_str,      # the same string you printed in 'Asset' (emoji/symbol/text)
                side_str,       # "LONG"/"SHORT"
                value_str,      # e.g., "$314.76"
                pnl_str,        # e.g., "$-45.77"
                lev_str,        # e.g., "17.16×"
                liq_str,        # e.g., "8.96"
                travel_str,     # e.g., "-13.35%"
            ])

    _totals = _ps_compute_totals(_rows_for_footer)

    # Build the one-line footer; Asset/Side/Liq are blank; Value/PnL are sums;
    # Lev/Travel are weighted averages (by Size if present; otherwise |Value|).
    line = (
        f"{'':<{WIDTHS['a']}} "
        f"{'':<{WIDTHS['s']}} "
        f"{_fmt_money(_totals.get('value')):>{WIDTHS['v']}} "
        f"{_fmt_money(_totals.get('pnl')):>{WIDTHS['p']}} "
        f"{_fmt_lev(_totals.get('avg_lev_weighted')):>{WIDTHS['l']}} "
        f"{'':>{WIDTHS['liq']}} "
        f"{_fmt_pct(_totals.get('avg_travel_weighted')):>{WIDTHS['t']}}"
    )

    # Make the totals row stand out a bit (bold + cyan). Remove styling if you prefer.
    BOLD = "\x1b[1m"
    CYAN = "\x1b[38;5;45m"
    RESET = "\x1b[0m"
    print(f"{CYAN}{BOLD}{line}{RESET}")


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


def print_positions_snapshot() -> None:
    """Resolve positions from storage and print the console table."""

    raw = _resolve_positions()
    rows = [_row_from_position(p) for p in raw]
    _print_positions_table(rows)


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
