# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Positions panel — shows ALL OPEN positions from dl.positions (no owner scoping).

Contract: render(dl, *_ignored, default_json_path=None)
We purposely ignore any 'csum' / snapshot arg; the panel queries the DB via dl.positions.

What we do:
- Source of truth: DataLocker.positions manager (db-backed)
- Try common manager methods (get_open_positions, get_positions, list, list_open, all, get_all)
- Filter to open positions if the manager returns both open/closed
- Render a compact table with totals
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

IC = "📊"
W_ASSET, W_SIDE, W_OWNER, W_VAL, W_PNL, W_LEV, W_LIQ = 10, 6, 26, 12, 12, 8, 10


# ───────────────────────── helpers ─────────────────────────

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
    if f >= 1_000_000_000: return f"{sign}${f/1_000_000_000:.1f}b".replace(".0b", "b")
    if f >= 1_000_000:     return f"{sign}${f/1_000_000:.1f}m".replace(".0m", "m")
    if f >= 1_000:         return f"{sign}${f/1_000:.1f}k".replace(".0k", "k")
    return f"{sign}${f:,.0f}" if f >= 100 else f"{sign}${f:.2f}"

def _is_open(row: Dict[str, Any]) -> bool:
    """Heuristics to decide if a position is open."""
    st = str(row.get("status") or "").lower()
    if st in {"closed", "settled", "liquidated", "exited"}:
        return False
    if isinstance(row.get("is_open"), bool):
        return bool(row["is_open"])
    # If a close marker exists, treat as closed
    for k in ("closed", "closed_at", "exit_price", "exit_ts"):
        if row.get(k) not in (None, "", 0):
            return False
    return True

def _normalize(x: Any) -> Dict[str, Any]:
    d = x if isinstance(x, dict) else getattr(x, "__dict__", {}) or {}
    # allow pydantic dump
    if not d:
        md = getattr(x, "model_dump", None)
        if callable(md):
            try: d = md()
            except Exception: d = {}
    return {
        "asset": d.get("asset") or d.get("symbol") or d.get("token") or "—",
        "side":  d.get("side") or d.get("direction") or "—",
        "owner": d.get("owner") or d.get("wallet") or d.get("account"),
        "value": d.get("value_usd") or d.get("usd") or d.get("value"),
        "pnl":   d.get("pnl_usd") or d.get("pnl") or 0.0,
        "lev":   d.get("leverage") or d.get("lev"),
        "liq":   d.get("liq_price") or d.get("liquidation") or d.get("liq"),
    }


# ───────────────────────── data access ─────────────────────────

def _read_all_from_manager(dl) -> (List[Dict[str, Any]], str):
    """
    Ask only dl.positions; do not read system vars or caches.
    Try common manager methods, then normalize & filter to OPEN.
    """
    src = "dl.positions"
    pmgr = getattr(dl, "positions", None)
    if not pmgr:
        return [], f"{src} (missing)"

    methods_in_order = [
        "get_open_positions",   # ideal if implemented
        "list_open",            # alt naming
        "get_positions",        # may return all; we'll filter
        "list",
        "all",
        "get_all",
    ]

    rows: List[Any] = []
    for name in methods_in_order:
        fn = getattr(pmgr, name, None)
        if not callable(fn):
            continue
        try:
            out = fn()
            if isinstance(out, list):
                rows = out
                src = f"{src}.{name}()"
                break
        except TypeError:
            # some get_positions(owner=None) signatures tolerate None
            try:
                out = fn(None)
                if isinstance(out, list):
                    rows = out
                    src = f"{src}.{name}(None)"
                    break
            except Exception:
                pass
        except Exception:
            pass

    if not rows:
        return [], f"{src} (no rows)"

    norm = [_normalize(r) for r in rows]
    open_only = [r for r in norm if _is_open(r)]
    return open_only, src


# ───────────────────────── rendering ─────────────────────────

def render(dl, *_ignored, default_json_path=None):
    rows, source = _read_all_from_manager(dl)

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
        val = _to_float(r["value"]) or 0.0
        pnl = _to_float(r["pnl"]) or 0.0
        tot_val += val
        tot_pnl += pnl

        line = (
            "    "
            + _pad(str(r["asset"]), W_ASSET)
            + _pad(str(r["side"]),  W_SIDE)
            + _pad(_short(r.get("owner")), W_OWNER)
            + _pad(_fmt_usd(val), W_VAL, "right")
            + _pad(_fmt_usd(pnl), W_PNL, "right")
            + _pad(str(r.get("lev") or "—"), W_LEV, "right")
            + _pad(str(r.get("liq") or "—"), W_LIQ, "right")
        )
        print(line)

    now = datetime.now()
    print(
        "    "
        + _pad("", W_ASSET + W_SIDE)
        + _pad("Totals:", W_OWNER)
        + _pad(_fmt_usd(tot_val), W_VAL, "right")
        + _pad(_fmt_usd(tot_pnl), W_PNL, "right")
        + _pad(now.strftime("%I:%M%p").lstrip("0").lower(), W_LEV + W_LIQ, "right")
    )
