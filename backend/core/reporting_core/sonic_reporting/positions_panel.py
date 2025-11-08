# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import os

# ========================= Layout =========================

HR_WIDTH = 78          # Outer rule width (all three rules share this width)
INDENT   = "  "        # Left margin

# Column widths (sum + 8*len(COL_SEP) ≈ HR_WIDTH - len(INDENT))
W_DIR   = 2            # "↑", "↓"
W_ASSET = 7            # e.g., "🟣 SOL"
W_SIZE  = 8            # numeric + unit glyph
W_VAL   = 9            # right aligned "$1,234"
W_PNL   = 9            # right aligned "+$123"/"−$12"
W_LEV   = 5            # "20.6×"
W_LIQ   = 7            # "$24500" or "d=12%"
W_HEAT  = 6            # "🔥12%" or "—"
W_TRVL  = 7            # "⇡ +8%" / "⇣ −3%" / "—"
COL_SEP = "  "

HEADER_ICONS = {
    "dir":   "↕",
    "asset": "●",
    "size":  "□",
    "value": "$",
    "pnl":   "±",
    "lev":   "×",
    "liq":   "💧",
    "heat":  "🔥",
    "trvl":  "⇆",
}

# ========================= Formatting helpers =========================

def _hr(title: str) -> str:
    content = f" 📊  {title} "
    pad = HR_WIDTH - len(content)
    if pad < 0:
        pad = 0
    left = pad // 2
    right = pad - left
    return INDENT + "─" * left + content + "─" * right


def _pad(text: str, width: int, right: bool = False) -> str:
    s = "" if text is None else str(text)
    n = len(s)
    if n >= width:
        return s[:width]
    return (" " * (width - n) + s) if right else (s + " " * (width - n))


def _fmt_usd(x: Any, width: int) -> str:
    try:
        v = float(x)
    except Exception:
        return _pad("—", width, right=True)
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000_000:
        s = f"{sign}${v/1_000_000_000:.1f}b".replace(".0b", "b")
    elif v >= 1_000_000:
        s = f"{sign}${v/1_000_000:.1f}m".replace(".0m", "m")
    elif v >= 1_000:
        s = f"{sign}${v/1_000:.1f}k".replace(".0k", "k")
    else:
        s = f"{sign}${v:,.2f}"
    return _pad(s, width, right=True)


def _fmt_pnl(x: Any) -> str:
    try:
        v = float(x)
    except Exception:
        return _pad("—", W_PNL, right=True)
    if v > 0:
        s = f"+${v:,.2f}"
    elif v < 0:
        s = f"−${abs(v):,.2f}"
    else:
        s = "$0.00"
    return _pad(s, W_PNL, right=True)


def _fmt_lev(x: Any) -> str:
    try:
        v = float(x)
        s = f"{v:.1f}×"
    except Exception:
        s = "—"
    return _pad(s, W_LEV, right=True)


def _fmt_liq(price: Any, dist: Any) -> str:
    # prefer absolute price
    try:
        p = float(price)
        if p > 0:
            return _pad(f"${p:,.0f}", W_LIQ, right=True)
    except Exception:
        pass
    # fallback to distance
    try:
        d = float(dist)
        return _pad(f"d={d:.0f}%", W_LIQ, right=True)
    except Exception:
        return _pad("—", W_LIQ, right=True)


def _fmt_heat(h: Any) -> str:
    try:
        v = float(h)
        if v > 0:
            return _pad(f"🔥{v:.0f}%", W_HEAT)
    except Exception:
        pass
    return _pad("—", W_HEAT)


def _fmt_travel(t: Any) -> str:
    try:
        v = float(t)
        if v > 0:
            return _pad(f"⇡ {v:+.0f}%", W_TRVL)
        if v < 0:
            return _pad(f"⇣ {v:+.0f}%", W_TRVL)
        return _pad("→  0%", W_TRVL)
    except Exception:
        return _pad("—", W_TRVL)


def _dir_arrow(side: Any) -> str:
    s = (str(side) or "").upper()
    if s.startswith("L"):
        return _pad("↑", W_DIR)   # LONG
    if s.startswith("S"):
        return _pad("↓", W_DIR)   # SHORT
    return _pad("·", W_DIR)


def _asset_chip(asset: Optional[str]) -> str:
    a = (asset or "").upper()
    glyph = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}.get(a, "•")
    # Keep it compact: "<icon> <TKR>"
    chip = f"{glyph} {a}" if a else glyph
    return _pad(chip, W_ASSET)


def _size_with_unit(size: Any, asset: Optional[str]) -> str:
    try:
        v = float(size)
    except Exception:
        return _pad("—", W_SIZE)
    unit = {"BTC": "₿", "XBT": "₿", "ETH": "Ξ", "SOL": "◎"}.get((asset or "").upper(), "")
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


def _now_hhmm() -> str:
    # Windows-safe, drop leading zero
    return datetime.now().strftime("%I:%M %p").lstrip("0").lower()


# ========================= Data access =========================

def _fetch_from_manager(dl: Any) -> List[Dict[str, Any]]:
    pmgr = getattr(dl, "positions", None)
    if not pmgr:
        return []
    for name in ("get_positions", "list", "get_all", "positions"):
        fn = getattr(pmgr, name, None)
        try:
            rows = fn() if callable(fn) else (fn if isinstance(fn, list) else None)
        except TypeError:
            try:
                rows = fn(None)  # tolerate get_positions(owner=None)
            except Exception:
                rows = None
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


def _read_positions_all(dl: Any) -> Tuple[List[Dict[str, Any]], str]:
    rows = _fetch_from_manager(dl)
    if rows:
        return rows, "dl.positions"
    rows = _fetch_from_db(dl)
    if rows:
        return rows, "db.positions"
    return [], "none"


# ========================= Normalization & filtering =========================

def _is_closed(d: Dict[str, Any]) -> bool:
    st = str(d.get("status") or "").lower()
    if st in {"closed", "settled", "exited", "liquidated"}:
        return True
    if isinstance(d.get("is_open"), bool):
        return not d["is_open"]
    for k in ("closed_at", "exit_ts", "exit_price"):
        if d.get(k) not in (None, "", 0):
            return True
    return False


def _normalize(d: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "asset": d.get("asset_type") or d.get("asset") or d.get("symbol") or d.get("token"),
        "side": d.get("position_type") or d.get("side") or d.get("direction"),
        "size": d.get("size") or d.get("qty") or d.get("quantity"),
        "value": d.get("value") or d.get("value_usd") or d.get("usd"),
        "pnl": d.get("pnl_after_fees_usd") or d.get("pnl_usd") or d.get("pnl"),
        "lev": d.get("leverage") or d.get("lev"),
        "liq_px": d.get("liquidation_price"),
        "liq_d": d.get("liquidation_distance"),
        "heat": d.get("current_heat_index") or d.get("heat_index"),
        "travel": d.get("travel_percent") or d.get("travel"),
    }


# ========================= Totals (history → fallback) =========================

def _latest_totals_from_history(dl: Any) -> Optional[Tuple[float, float, Optional[str]]]:
    try:
        cur = dl.db.get_cursor()
        cur.execute("SELECT * FROM positions_totals_history ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None
        d = {col[0]: val for col, val in zip(cur.description, row)}
        # discover fields
        val_key = next((k for k in ("total_value_usd", "total_value", "value_usd", "value") if k in d and d[k] is not None), None)
        pnl_key = next((k for k in ("total_pnl_usd", "pnl_usd", "total_pnl", "pnl") if k in d and d[k] is not None), None)
        ts_key = next((k for k in ("ts", "timestamp", "updated_at", "created_at", "asof", "time", "at") if k in d and d[k]), None)
        if not val_key or not pnl_key:
            return None
        val = float(d[val_key])
        pnl = float(d[pnl_key])
        tstr: Optional[str] = None
        if ts_key:
            ts_val = d[ts_key]
            try:
                if isinstance(ts_val, (int, float)):
                    dt = datetime.fromtimestamp(float(ts_val), tz=timezone.utc)
                else:
                    # tolerate plain ISO or ISO with Z
                    t = str(ts_val)
                    dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                tstr = dt.astimezone().strftime("%I:%M %p").lstrip("0").lower()
                # freshness gate: default to 2× interval (seconds)
                interval = int(os.getenv("SONIC_INTERVAL_SEC", "30"))
                max_age = 2 * max(1, interval)
                age = (datetime.now(timezone.utc) - dt).total_seconds()
                if age > max_age:
                    tstr = None  # too old; trigger fallback
            except Exception:
                tstr = None
        return (val, pnl, tstr)
    except Exception:
        return None


# ========================= Render =========================

def render(dl, csum=None, default_json_path: Optional[str] = None) -> None:
    raw, source = _read_positions_all(dl)

    # Normalize & filter open
    rows = []
    for r in raw:
        d = r if isinstance(r, dict) else (getattr(r, "dict", lambda: {})() or getattr(r, "__dict__", {}) or {})
        if not _is_closed(d):
            rows.append(_normalize(d))

    # Header & column titles (with icons)
    print()
    print(_hr("Positions (ALL)"))
    header = (
        INDENT
        + _pad(f"{HEADER_ICONS['dir']}", W_DIR) + COL_SEP
        + _pad(f"{HEADER_ICONS['asset']}Asset", W_ASSET) + COL_SEP
        + _pad(f"{HEADER_ICONS['size']}Size",  W_SIZE) + COL_SEP
        + _pad(f"{HEADER_ICONS['value']}Value", W_VAL) + COL_SEP
        + _pad(f"{HEADER_ICONS['pnl']}PnL",    W_PNL) + COL_SEP
        + _pad(f"{HEADER_ICONS['lev']}Lev",    W_LEV) + COL_SEP
        + _pad(f"{HEADER_ICONS['liq']}Liq",    W_LIQ) + COL_SEP
        + _pad(f"{HEADER_ICONS['heat']}Heat",  W_HEAT) + COL_SEP
        + _pad(f"{HEADER_ICONS['trvl']}Travel",W_TRVL)
    )
    print(header)
    print(INDENT + "─" * HR_WIDTH)

    if not rows:
        print(f"{INDENT}[POSITIONS] source: {source} (0 rows)")
        print(f"{INDENT}(no positions)")
        print(INDENT + "─" * HR_WIDTH)
        return

    # Sort by value desc
    rows.sort(key=lambda z: float(z["value"] or 0) if z.get("value") is not None else 0.0, reverse=True)

    live_total_value = 0.0
    live_total_pnl   = 0.0

    for d in rows:
        val = float(d["value"]) if d["value"] is not None else 0.0
        pnl = float(d["pnl"])   if d["pnl"]   is not None else 0.0
        live_total_value += val
        live_total_pnl   += pnl

        line = (
            INDENT
            + _dir_arrow(d["side"]) + COL_SEP
            + _asset_chip(d["asset"]) + COL_SEP
            + _size_with_unit(d["size"], d["asset"]) + COL_SEP
            + _fmt_usd(val, W_VAL) + COL_SEP
            + _fmt_pnl(pnl) + COL_SEP
            + _fmt_lev(d["lev"]) + COL_SEP
            + _fmt_liq(d["liq_px"], d["liq_d"]) + COL_SEP
            + _fmt_heat(d["heat"]) + COL_SEP
            + _fmt_travel(d["travel"])
        )
        print(line)

    print(INDENT + "─" * HR_WIDTH)

    # Totals from history if fresh, else live compute
    hist = _latest_totals_from_history(dl)
    if hist and hist[2] is not None:
        tot_val, tot_pnl, ts_str = hist
    else:
        tot_val, tot_pnl, ts_str = live_total_value, live_total_pnl, _now_hhmm()

    # Compose totals line aligned under Value/PnL
    prefix_len = len(INDENT) + W_DIR + len(COL_SEP) + W_ASSET + len(COL_SEP) + W_SIZE + len(COL_SEP)
    prefix = " " * prefix_len + "Totals → "
    tail = (
        _fmt_usd(tot_val, W_VAL) + COL_SEP
        + _fmt_pnl(tot_pnl) + COL_SEP
        + (ts_str or _now_hhmm())
    )
    line = INDENT + prefix.strip().rjust(len(prefix)) + tail
    # Ensure exact width by padding if needed
    if len(line) < len(INDENT) + HR_WIDTH:
        line = line + " " * (len(INDENT) + HR_WIDTH - len(line))
    print(line)
    print(INDENT + "─" * HR_WIDTH)
