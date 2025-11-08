# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime

# widths
W_ASSET, W_SIDE, W_OWNER, W_VAL, W_PNL, W_LEV, W_LIQ = 12, 8, 28, 12, 12, 8, 10


def _pad(s: str, n: int, align: str = "left") -> str:
    s = "" if s is None else str(s)
    if len(s) >= n: return s[:n]
    pad = " " * (n - len(s))
    return (s + pad) if align == "left" else (pad + s)


def _short(addr: Optional[str], l=6, r=6) -> str:
    if not addr: return "—"
    a = str(addr).strip()
    return a if len(a) <= l + r + 1 else f"{a[:l]}…{a[-r:]}"


def _to_float(x: Any) -> Optional[float]:
    try: return float(x)
    except Exception: return None


def _fmt_usd(v: Any) -> str:
    f = _to_float(v)
    if f is None: return "—"
    sign = "-" if f < 0 else ""
    f = abs(f)
    if f >= 1_000_000_000: return f"{sign}${f/1_000_000_000:.1f}b".replace(".0b","b")
    if f >= 1_000_000:     return f"{sign}${f/1_000_000:.1f}m".replace(".0m","m")
    if f >= 1_000:         return f"{sign}${f/1_000:.1f}k".replace(".0k","k")
    return f"{sign}${f:,.0f}" if f >= 100 else f"{sign}${f:.2f}"


def _is_closed(d: Dict[str, Any]) -> bool:
    st = str(d.get("status") or "").lower()
    if st in {"closed", "settled", "exited", "liquidated"}:
        return True
    if isinstance(d.get("is_open"), bool):
        return not d["is_open"]
    # if an explicit exit marker exists
    for k in ("closed_at", "exit_ts", "exit_price"):
        if d.get(k) not in (None, "", 0):
            return True
    return False


def _normalize(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "asset": d.get("asset") or d.get("symbol") or d.get("token") or "—",
        "side":  d.get("side") or d.get("direction") or "—",
        "owner": d.get("owner") or d.get("wallet") or d.get("account"),
        "value": d.get("value_usd") or d.get("usd") or d.get("value"),
        "pnl":   d.get("pnl_usd") or d.get("pnl"),
        "lev":   d.get("leverage") or d.get("lev"),
        "liq":   d.get("liq_price") or d.get("liquidation") or d.get("liq"),
    }


# ---- data access -------------------------------------------------------------

def _fetch_from_manager(dl: Any) -> List[Dict[str, Any]]:
    pmgr = getattr(dl, "positions", None)
    if not pmgr: return []
    # try common shapes
    for name in ("get_positions", "list", "get_all", "positions"):
        fn = getattr(pmgr, name, None)
        rows = None
        try:
            if callable(fn):
                rows = fn()
            elif isinstance(fn, list):
                rows = fn
        except TypeError:
            # tolerate signatures like get_positions(owner=None)
            try:
                rows = fn(None) if callable(fn) else None
            except Exception:
                rows = None
        except Exception:
            rows = None
        if isinstance(rows, list) and rows:
            return [r if isinstance(r, dict) else getattr(r, "__dict__", {}) or {} for r in rows]
    return []


def _fetch_from_db(dl: Any) -> List[Dict[str, Any]]:
    try:
        cur = dl.db.get_cursor()
        cur.execute("SELECT * FROM positions")
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return rows
    except Exception:
        return []


def _read_positions_all(dl: Any) -> (List[Dict[str, Any]], str):
    # Manager first (preferred), then direct DB fallback
    mrows = _fetch_from_manager(dl)
    if mrows:
        return mrows, "dl.positions"
    drows = _fetch_from_db(dl)
    if drows:
        return drows, "db.positions"
    return [], "none"


# ---- rendering ---------------------------------------------------------------

def render(dl, *_unused, default_json_path: Optional[str] = None):
    raw, source = _read_positions_all(dl)
    # normalize + filter open
    rows = []
    for r in raw:
        d = _normalize(r if isinstance(r, dict) else getattr(r, "__dict__", {}) or {})
        if not _is_closed(r if isinstance(r, dict) else {}):
            rows.append(d)

    print("\n  ---------------------- 📊  Positions  -----------------------")
    print(f"  [POSITIONS] source: {source} ({len(rows)} rows)")
    if not rows:
        print("  (no positions)")
        return

    # sort by value desc
    def _val(x): 
        v = _to_float(x.get("value"))
        return v if v is not None else 0.0
    rows.sort(key=_val, reverse=True)

    header = (
        "    "
        + _pad("Asset", W_ASSET)
        + _pad("Side",  W_SIDE)
        + _pad("Owner", W_OWNER)
        + _pad("Value", W_VAL, "right")
        + _pad("PnL",   W_PNL, "right")
        + _pad("Lev",   W_LEV, "right")
        + _pad("Liq",   W_LIQ, "right")
    )
    print(header)

    tot_val = 0.0
    tot_pnl = 0.0
    for r in rows:
        val = _to_float(r.get("value")) or 0.0
        pnl = _to_float(r.get("pnl")) or 0.0
        tot_val += val
        tot_pnl += pnl

        print(
            "    "
            + _pad(str(r.get("asset") or "—"), W_ASSET)
            + _pad(str(r.get("side")  or "—"), W_SIDE)
            + _pad(_short(r.get("owner")), W_OWNER)
            + _pad(_fmt_usd(val), W_VAL, "right")
            + _pad(_fmt_usd(pnl), W_PNL, "right")
            + _pad(str(r.get("lev") or "—"), W_LEV, "right")
            + _pad(str(r.get("liq") or "—"), W_LIQ, "right")
        )

    now = datetime.now()
    print(
        "    "
        + _pad("", W_ASSET + W_SIDE)
        + _pad("Totals:", W_OWNER)
        + _pad(_fmt_usd(tot_val), W_VAL, "right")
        + _pad(_fmt_usd(tot_pnl), W_PNL, "right")
        + _pad(now.strftime("%I:%M%p").lstrip("0").lower(), W_LEV + W_LIQ, "right")
    )
