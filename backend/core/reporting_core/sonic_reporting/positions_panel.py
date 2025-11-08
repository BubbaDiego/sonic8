# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime

# ========================= Formatting =========================

HR_WIDTH = 90                 # total width of the three horizontal rules (keep consistent)
INDENT   = "  "               # left margin for the panel

# Column widths (sum + spaces should fit under HR_WIDTH)
W_DIR    = 3                  # "↑ " / "↓ "
W_ASSET  = 12
W_SIZE   = 14
W_VAL    = 12                 # right-aligned "$1,234"
W_PNL    = 11                 # right-aligned "+$123" / "−$12"
W_LEV    = 7                  # "3.0×"
W_LIQ    = 10                 # "$24,500" or "—"
W_HEAT   = 9                  # "🔥12%" or "—"
W_TRVL   = 9                  # "⇡ +8%" / "⇣ −3%"/ "—"

COL_SEP  = "  "               # spacing between columns

def _hr(title: str) -> str:
    content = f" 📊  {title} "
    pad = HR_WIDTH - len(content)
    if pad < 0:  # safety
        pad = 0
    left = pad // 2
    right = pad - left
    return INDENT + "─" * left + content + "─" * right

def _pad(text: str, width: int, right: bool = False) -> str:
    s = "" if text is None else str(text)
    n = len(s)
    if n >= width:
        return s[:width]
    if right:
        return " " * (width - n) + s
    return s + " " * (width - n)

def _fmt_usd(x: Any) -> str:
    try:
        v = float(x)
    except Exception:
        return " " * (W_VAL)  # preserve width if unknown
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000_000: s = f"{sign}${v/1_000_000_000:.1f}b".replace(".0b","b")
    elif v >= 1_000_000:   s = f"{sign}${v/1_000_000:.1f}m".replace(".0m","m")
    elif v >= 1_000:       s = f"{sign}${v/1_000:.1f}k".replace(".0k","k")
    else:                  s = f"{sign}${v:,.2f}"
    return _pad(s, W_VAL, right=True)

def _fmt_pnl(x: Any) -> str:
    try:
        v = float(x)
    except Exception:
        return _pad("—", W_PNL, right=True)
    sgn = "+" if v > 0 else ("−" if v < 0 else "")
    v = abs(v)
    s  = f"{sgn}${v:,.2f}"
    return _pad(s, W_PNL, right=True)

def _fmt_lev(x: Any) -> str:
    try:
        v = float(x)
        s = f"{v:.1f}×"
    except Exception:
        s = "—"
    return _pad(s, W_LEV, right=True)

def _fmt_liq(price: Any, dist: Any) -> str:
    try:
        p = float(price)
        if p > 0:
            return _pad(f"${p:,.0f}", W_LIQ, right=True)
    except Exception:
        pass
    try:
        d = float(dist)
        s = f"d={d:.0f}%"
        return _pad(s, W_LIQ, right=True)
    except Exception:
        return _pad("—", W_LIQ, right=True)

def _fmt_heat(h: Any) -> str:
    try:
        v = float(h)
        if v > 0:
            return _pad(f"🔥{v:.0f}%", W_HEAT, right=False)
    except Exception:
        pass
    return _pad("—", W_HEAT)

def _fmt_travel(t: Any) -> str:
    try:
        v = float(t)
        arrow = "⇡" if v > 0 else ("⇣" if v < 0 else "→")
        s = f"{arrow} {v:+.0f}%"
        return _pad(s, W_TRVL, right=False)
    except Exception:
        return _pad("—", W_TRVL)

def _dir_arrow(side: Any) -> str:
    s = (str(side) or "").upper()
    if s.startswith("L"): return _pad("↑", W_DIR)   # LONG
    if s.startswith("S"): return _pad("↓", W_DIR)   # SHORT
    return _pad("·", W_DIR)

def _size_with_unit(size: Any, asset: str) -> str:
    try:
        v = float(size)
    except Exception:
        return _pad("—", W_SIZE)
    unit = {
        "BTC": "₿", "XBT": "₿",
        "ETH": "Ξ",
        "SOL": "◎",
        "USDC":"", "USDT":"", "USD":""
    }.get((asset or "").upper(), "")
    # compact formatting: integers show no decimals, small sizes show 2–4 decimals
    if v == 0:
        s = "0"
    elif abs(v) >= 100:
        s = f"{int(v)}"
    elif abs(v) >= 1:
        s = f"{v:.2f}"
    elif abs(v) >= 0.01:
        s = f"{v:.3f}"
    else:
        s = f"{v:.4f}"
    return _pad(f"{s}{unit}", W_SIZE)

# ========================= Data access =========================

def _fetch_from_manager(dl: Any) -> List[Dict[str, Any]]:
    mgr = getattr(dl, "positions", None)
    if not mgr:
        return []
    for name in ("get_positions", "list", "get_all", "positions"):
        fn = getattr(mgr, name, None)
        rows = None
        try:
            if callable(fn):
                try:
                    rows = fn()             # preferred: all positions
                except TypeError:
                    rows = fn(None)         # tolerate get_positions(owner=None)
            elif isinstance(fn, list):
                rows = fn
        except Exception:
            rows = None
        if isinstance(rows, list) and rows:
            return [r if isinstance(r, dict) else (getattr(r, "__dict__", {}) or {}) for r in rows]
    return []

def _fetch_from_db(dl: Any) -> List[Dict[str, Any]]:
    try:
        cur = dl.db.get_cursor()
        cur.execute("SELECT * FROM positions")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []

def _read_positions_all(dl: Any) -> tuple[list[dict], str]:
    rows = _fetch_from_manager(dl)
    if rows:
        return rows, "dl.positions"
    rows = _fetch_from_db(dl)
    if rows:
        return rows, "db.positions"
    return [], "none"

# ========================= Normalization =========================

def _is_closed(d: Dict[str, Any]) -> bool:
    st = str(d.get("status") or "").lower()
    if st in ("closed", "settled", "exited", "liquidated"):
        return True
    if isinstance(d.get("is_open"), bool):
        return not d["is_open"]
    for k in ("closed_at", "exit_ts", "exit_price"):
        if d.get(k) not in (None, "", 0):
            return True
    return False

def _normalize(d: Dict[str, Any]) -> Dict[str, Any]:
    # Prefer richer names from your model; fall back to generic DB column names
    return {
        "asset" : d.get("asset_type") or d.get("asset") or d.get("symbol") or d.get("token") or "",
        "side"  : d.get("position_type") or d.get("side") or d.get("direction") or "",
        "size"  : d.get("size") or d.get("qty") or d.get("quantity"),
        "value" : d.get("value") or d.get("value_usd") or d.get("usd"),
        "pnl"   : d.get("pnl_after_fees_usd") or d.get("pnl_usd") or d.get("pnl"),
        "lev"   : d.get("leverage") or d.get("lev"),
        "liq_px": d.get("liquidation_price"),
        "liq_d" : d.get("liquidation_distance"),
        "heat"  : d.get("current_heat_index") or d.get("heat_index"),
        "travel": d.get("travel_percent") or d.get("travel"),
    }

# ========================= Render =========================

def render(dl, csum=None, default_json_path: Optional[str] = None) -> None:
    raw, source = _read_positions_all(dl)
    if not raw:
        print()
        print(_hr("Positions (ALL)"))
        # header line
        hdr = (
            INDENT
            + _pad("Dir", W_DIR) + COL_SEP
            + _pad("Asset", W_ASSET) + COL_SEP
            + _pad("Size", W_SIZE) + COL_SEP
            + _pad("Value", W_VAL, right=True) + COL_SEP
            + _pad("PnL", W_PNL, right=True) + COL_SEP
            + _pad("Lev", W_LEV, right=True) + COL_SEP
            + _pad("Liq Px", W_LIQ, right=True) + COL_SEP
            + _pad("🔥Heat", W_HEAT) + COL_SEP
            + _pad("⇆Travel", W_TRVL)
        )
        print(hdr)
        print(INDENT + "─" * (HR_WIDTH))
        print(f"{INDENT}[POSITIONS] source: {source} (0 rows)")
        print(f"{INDENT}(no positions)")
        print(INDENT + "─" * (HR_WIDTH))
        return

    # normalize + filter open
    rows = []
    for r in raw:
        d = r if isinstance(r, dict) else (getattr(r, "__dict__", {}) or {})
        if not _is_closed(d):
            rows.append(_normalize(d))

    # sort by value desc
    rows.sort(key=lambda z: float(z["value"] or 0) if z.get("value") is not None else 0.0, reverse=True)

    # header
    print()
    print(_hr("Positions (ALL)"))
    hdr = (
        INDENT
        + _pad("Dir", W_DIR) + COL_SEP
        + _pad("Asset", W_ASSET) + COL_SEP
        + _pad("Size", W_SIZE) + COL_SEP
        + _pad("Value", W_VAL, right=True) + COL_SEP
        + _pad("PnL", W_PNL, right=True) + COL_SEP
        + _pad("Lev", W_LEV, right=True) + COL_SEP
        + _pad("Liq Px", W_LIQ, right=True) + COL_SEP
        + _pad("🔥Heat", W_HEAT) + COL_SEP
        + _pad("⇆Travel", W_TRVL)
    )
    print(hdr)
    print(INDENT + "─" * (HR_WIDTH))

    tot_val = 0.0
    tot_pnl = 0.0

    for d in rows:
        try:
            val = float(d["value"]) if d["value"] is not None else 0.0
        except Exception:
            val = 0.0
        try:
            pnl = float(d["pnl"]) if d["pnl"] is not None else 0.0
        except Exception:
            pnl = 0.0
        tot_val += val
        tot_pnl += pnl

        line = (
            INDENT
            + _dir_arrow(d["side"]) + COL_SEP
            + _pad(d["asset"] or "—", W_ASSET) + COL_SEP
            + _size_with_unit(d["size"], d["asset"]) + COL_SEP
            + _fmt_usd(val) + COL_SEP
            + _fmt_pnl(pnl) + COL_SEP
            + _fmt_lev(d["lev"]) + COL_SEP
            + _fmt_liq(d["liq_px"], d["liq_d"]) + COL_SEP
            + _fmt_heat(d["heat"]) + COL_SEP
            + _fmt_travel(d["travel"])
        )
        print(line)

    # footer (totals + time, same width line)
    print(INDENT + "─" * (HR_WIDTH))
    right = f"{_fmt_usd(tot_val).strip():>12}  {_fmt_pnl(tot_pnl).strip():>11}  {datetime.now().strftime('%-I:%M %p').lower()}"
    left = " " * (len(INDENT) + W_DIR + len(COL_SEP) + W_ASSET + len(COL_SEP) + W_SIZE + len(COL_SEP)) + "Totals → "
    # pad the middle so total line reaches the same HR_WIDTH
    fixed = INDENT + (left + right)
    if len(fixed) < HR_WIDTH + len(INDENT):
        fixed = fixed + " " * (HR_WIDTH + len(INDENT) - len(fixed))
    print(fixed)
    print(INDENT + "─" * (HR_WIDTH))
