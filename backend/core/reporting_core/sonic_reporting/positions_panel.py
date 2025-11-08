# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import unicodedata
import os

# ============================================================
# CONFIG: colors (only text is colored; bars remain plain)
USE_COLOR     = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0", "false", "no", "off"}
TITLE_COLOR   = "\x1b[38;5;45m"   # cyan/teal for "Positions (ALL)" text
TOTALS_COLOR  = "\xb3[38;5;214m"  # amber/orange for totals row text

def _c(s: str, color: str) -> str:
    return f"{color}{s}\x1b[0m" if USE_COLOR else s
# ============================================================

# ====== Layout ======
HR_WIDTH = 78
INDENT   = "  "

# Compact column widths (~78 chars incl. separators)
W_DIR   = 2      # 🔺/🔻
W_ASSET = 7      # e.g., "🟣 SOL"
W_SIZE  = 8
W_VAL   = 9
W_PNL   = 9
W_LEV   = 5
W_LIQ   = 7
W_HEAT  = 6
W_TRVL  = 7
COL_SEP = "  "

HEADER_ICONS = {
    "dir":   "↕",
    "asset": "🪙",
    "size":  "📦",
    "value": "💵",
    "pnl":   "💹",
    "lev":   "🧮",
    "liq":   "💧",
    "heat":  "🔥",
    "trvl":  "🔁",
}

# ====== Display-width aware padding (emoji-safe) ======
_VARIATION_SELECTORS = {0xFE0F, 0xFE0E}
_ZERO_WIDTH = {0x200D, 0x200C}

def _disp_len(s: str) -> int:
    """Approximate terminal cell width (treat East Asian Wide/Full as width 2; ignore ZWJ/VS)."""
    total = 0
    for ch in s:
        cp = ord(ch)
        if cp in _VARIATION_SELECTORS or cp in _ZERO_WIDTH:
            continue
        ew = unicodedata.east_asian_width(ch)  # <-- fixed typo here
        total += 2 if ew in ("W", "F") else 1
    return total

def _padw(text: Any, width: int, *, right: bool = False) -> str:
    s = "" if text is None else str(text)
    cur = _disp_len(s)
    if cur >= width:
        # Trim to fit by removing trailing code points until width ok.
        while s and _disp_len(s) > width:
            s = s[:-1]
        return s
    pad = " " * (width - cur)
    return (pad + s) if right else (s + pad)

def _pad(s: Any, w: int, right: bool = False) -> str:
    return _padw(s, w, right=right)

# ====== Formatting ======
def _hr(title: str) -> str:
    # Color only the text; bars left/right remain plain
    plain = f" 📊  {title} "
    colored = f" {_c('📊  ' + title, TITLE_COLOR)} "
    pad = HR_WIDTH - len(plain)
    if pad < 0: pad = 0
    L = pad // 2
    R = pad - L
    return INDENT + "─" * L + colored + "─" * R

def _fmt_usd(x: Any, w: int, *, right: bool = True) -> str:
    try:
        v = float(x)
    except Exception:
        return _pad("—", w, right=right)
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1e9:   s = f"{sign}${v/1e9:.1f}b".replace(".0b","b")
    elif v >= 1e6: s = f"{sign}${v/1e6:.1f}m".replace(".0m","m")
    elif v >= 1e3: s = f"{sign}${v/1e3:.1f}k".replace(".0k","k")
    else:          s = f"{sign}${v:,.2f}"
    return _pad(s, w, right=right)

def _fmt_pnl(x: Any, *, right: bool = True) -> str:
    try:
        v = float(x)
    except Exception:
        return _pad("—", W_PNL, right=right)
    if v > 0:   s = f"+${v:,.2f}"
    elif v < 0: s = f"−${abs(v):,.2f}"
    else:       s = "$0.00"
    return _pad(s, W_PNL, right=right)

def _fmt_lev(x: Any, *, right: bool = True) -> str:
    try:
        v = float(x); s = f"{v:.1f}×"
    except Exception:
        s = "—"
    return _pad(s, W_LEV, right=right)

def _fmt_liq(p: Any, d: Any) -> str:
    try:
        v = float(p)
        if v > 0: return _pad(f"${int(round(v))}", W_LIQ, right=True)
    except Exception:
        pass
    try:
        dd = float(d); return _pad(f"d={int(round(dd))}%", W_LIQ, right=True)
    except Exception:
        return _pad("—", W_LIQ, right=True)

def _fmt_heat(x: Any, *, right: bool = False) -> str:
    try:
        v = float(x); return _pad(f"🔥{int(round(v))}%", W_HEAT, right=right)
    except Exception:
        return _pad("—", W_HEAT, right=right)

def _fmt_travel(x: Any, *, right: bool = False) -> str:
    try:
        v = float(x); arrow = "⇡" if v > 0 else ("⇣" if v < 0 else "→")
        return _pad(f"{arrow} {v:+.0f}%", W_TRVL, right=right)
    except Exception:
        return _pad("—", W_TRVL, right=right)

def _dir_arrow(side: Any) -> str:
    s = (str(side) or "").upper()
    if s.startswith("L"): return _pad("🔺", W_DIR)  # LONG
    if s.startswith("S"): return _pad("🔻", W_DIR)  # SHORT
    return _pad("·", W_DIR)

def _asset_chip(asset: Optional[str]) -> str:
    a = (asset or "").upper()
    glyph = {"BTC":"🟡","ETH":"🔷","SOL":"🟣"}.get(a, "•")
    return _pad(f"{glyph} {a}" if a else glyph, W_ASSET)

def _normalize_size_for_display(asset: Optional[str], size: Any, value: Any) -> float:
    """
    If size is clearly over-scaled vs USD value (value/size < ~0.2),
    progressively divide by 10 (max 1e6) until ratio looks sensible.
    """
    try:
        s = float(size)
    except Exception:
        return 0.0
    try:
        v = float(value)
    except Exception:
        return s
    if s <= 0: return s
    ratio = v / s
    if ratio >= 0.2: return s
    scale = 1.0
    for _ in range(6):
        t = s / scale
        if t <= 0: break
        if v / t >= 0.2:
            return t
        scale *= 10.0
    return s / scale

def _fmt_size(asset: Optional[str], size_adj: float, *, right: bool = False) -> str:
    unit = {"BTC":"₿","XBT":"₿","ETH":"Ξ","SOL":"◎"}.get((asset or "").upper(), "")
    s = size_adj
    if s == 0:        txt = "0"
    elif abs(s) >= 1e3: txt = f"{int(round(s))}"
    elif abs(s) >= 1:   txt = f"{s:.2f}"
    elif abs(s) >= .01: txt = f"{s:.3f}"
    else:               txt = f"{s:.4f}"
    return _pad(f"{txt}{unit}", W_SIZE, right=right)

# ====== Data access ======
def _fetch_from_manager(dl: Any) -> List[Dict[str, Any]]:
    pmgr = getattr(dl, "positions", None)
    if not pmgr: return []
    for name in ("get_positions","list","get_all","positions"):
        fn = getattr(pmgr, name, None)
        try:
            rows = fn() if callable(fn) else (fn if isinstance(fn,list) else None)
        except TypeError:
            try: rows = fn(None)
            except Exception: rows = None
        except Exception:
            rows = None
        if isinstance(rows, list) and rows:
            return [r if isinstance(r,dict) else (getattr(r,"dict",lambda:{})() or getattr(r,"__dict__",{}) or {}) for r in rows]
    return []

def _fetch_from_db(dl: Any) -> List[Dict[str, Any]]:
    try:
        cur = dl.db.get_cursor()
        cur.execute("SELECT * FROM positions")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols,row)) for row in cur.fetchall()]
    except Exception:
        return []

def _read_positions_all(dl: Any) -> Tuple[List[Dict[str, Any]], str]:
    rows = _fetch_from_manager(dl)
    if rows: return rows, "dl.positions"
    rows = _fetch_from_db(dl)
    return (rows,"db.positions") if rows else ([], "none")

# ====== Normalization & filtering ======
def _is_open(d: Dict[str,Any]) -> bool:
    st = (d.get("status") or "").lower()
    if st in {"closed","settled","exited","liquidated"}: return False
    if isinstance(d.get("is_open"), bool): return d["is_open"]
    for k in ("closed","closed_at","exit_ts","exit_price"):
        if d.get(k) not in (None,"",0): return False
    return True

def _normalize(d: Dict[str,Any]) -> Dict[str,Any]:
    return {
        "asset": d.get("asset_type") or d.get("asset") or d.get("symbol") or d.get("token"),
        "side":  d.get("position_type") or d.get("side") or d.get("direction"),
        "size":  d.get("size") or d.get("qty") or d.get("quantity"),
        "value": d.get("value") or d.get("value_usd") or d.get("usd"),
        "pnl":   d.get("pnl_after_fees_usd") or d.get("pnl_usd") or d.get("pnl"),
        "lev":   d.get("leverage") or d.get("lev"),
        "liq_p": d.get("liquidation_price"),
        "liq_d": d.get("liquidation_distance"),
        "heat":  d.get("current_heat_index") or d.get("heat_index"),
        "trav":  d.get("travel_percent") or d.get("travel"),
    }

# ====== Render ======
def render(dl, *_args, **_kw) -> None:
    raw, source = _read_positions_all(dl)
    rows: List[Dict[str,Any]] = []
    for r in raw:
        d = r if isinstance(r,dict) else (getattr(r,"dict",lambda:{})() or getattr(r,"__dict__",{}) or {})
        if _is_open(d):
            rows.append(_normalize(d))

    print()
    print(_hr("Positions (ALL)"))
    header = (
        INDENT
        + _pad(HEADER_ICONS["dir"],   W_DIR)                              + COL_SEP
        + _pad(HEADER_ICONS["asset"] + "Asset",  W_ASSET)                 + COL_SEP
        + _pad(HEADER_ICONS["size"]  + "Size",   W_SIZE)                  + COL_SEP
        + _pad(HEADER_ICONS["value"] + "Value",  W_VAL)                   + COL_SEP
        + _pad(HEADER_ICONS["pnl"]   + "PnL",    W_PNL)                   + COL_SEP
        + _pad(HEADER_ICONS["lev"]   + "Lev",    W_LEV)                   + COL_SEP
        + _pad(HEADER_ICONS["liq"]   + "Liq",    W_LIQ)                   + COL_SEP
        + _pad(HEADER_ICONS["heat"]  + "Heat",   W_HEAT)                  + COL_SEP
        + _pad(HEADER_ICONS["trvl"]  + "Travel", W_TRVL)
    )
    print(header)
    print(INDENT + "─"*HR_WIDTH)

    if not rows:
        print(f"{INDENT}[POSITIONS] source: {source} (0 rows)")
        print(f"{INDENT}(no positions)")
        print()  # breathing room
        return

    # sort by value desc
    rows.sort(key=lambda z: float(z["value"] or 0) if z["value"] is not None else 0.0)

    # Totals accumulators (size-weighted for lev/heat/travel)
    sum_size = sum_val = sum_pnl = 0.0
    w_lev_n = w_heat_n = w_trv_n = w_den = 0.0

    for d in reversed(rows):  # show biggest value last (like your screenshot)
        size_adj = _normalize_size_for_display(d["asset"], d["size"], d["value"])
        val = float(d["value"] or 0.0)
        pnl = float(d["pnl"]   or 0.0)

        sum_size += size_adj
        sum_val  += val
        sum_pnl  += pnl

        wt = max(0.0, size_adj)
        try: w_lev_n  += float(d["lev"])  * wt
        except Exception: pass
        try: w_heat_n += float(d["heat"]) * wt
        except Exception: pass
        try: w_trv_n  += float(d["trav"]) * wt
        except Exception: pass
        w_den += wt

        print(
            INDENT
            + _dir_arrow(d["side"])                        + COL_SEP
            + _asset_chip(d["asset"])                      + COL_SEP
            + _fmt_size(d["asset"], size_adj, right=False) + COL_SEP
            + _fmt_usd(val, W_VAL, right=True)             + COL_SEP
            + _fmt_pnl(pnl, right=True)                    + COL_SEP
            + _fmt_lev(d["lev"], right=True)               + COL_SEP
            + _fmt_liq(d["liq_p"], d["liq_d"])             + COL_SEP
            + _fmt_heat(d["heat"], right=False)            + COL_SEP
            + _fmt_travel(d["trav"], right=False)
        )

    # Totals (left-justified cells, colored text; no trailing rule, one blank line after)
    avg_lev  = (w_lev_n  / w_den) if w_den > 0 else None
    avg_heat = (w_heat_n / w_den) if w_den > 0 else None
    avg_trav = (w_trv_n  / w_den) if w_den > 0 else None

    totals_plain = (
        INDENT
        + _pad("", W_DIR)                                 + COL_SEP
        + _pad("Totals", W_ASSET)                         + COL_SEP
        + _fmt_size("", sum_size, right=False)            + COL_SEP
        + _fmt_usd(sum_val, W_VAL, right=False)           + COL_SEP
        + _fmt_pnl(sum_pnl, right=False)                  + COL_SEP
        + _pad(f"{avg_lev:.1f}×" if avg_lev is not None else "—", W_LEV, right=False) + COL_SEP
        + _pad("—", W_LIQ, right=False)                   + COL_SEP
        + _fmt_heat(avg_heat, right=False)                + COL_SEP
        + _fmt_travel(avg_trav, right=False)
    )
    print(_c(totals_plain, TOTALS_COLOR))
    print()  # one blank line after totals
