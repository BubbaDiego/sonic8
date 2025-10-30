# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import importlib
import time

try:
    rich_console = importlib.import_module("rich.console"); Console = getattr(rich_console, "Console")
    rich_table   = importlib.import_module("rich.table");   Table   = getattr(rich_table, "Table")
    rich_box     = importlib.import_module("rich.box");     BOX     = getattr(rich_box, "SIMPLE_HEAVY")
    rich_text    = importlib.import_module("rich.text");    Text    = getattr(rich_text, "Text")
    _HAS_RICH = True
except Exception:
    _HAS_RICH = False
    Console = Table = BOX = Text = None  # type: ignore

console = Console() if _HAS_RICH else None

ICON_BTC = "🟡"; ICON_ETH = "🔷"; ICON_SOL = "🟣"

def _abbr(n):
    try:
        v = float(n)
    except Exception:
        return "—"
    if abs(v) >= 1_000_000_000: return f"{v/1_000_000_000:.1f}B"
    if abs(v) >= 1_000_000:     return f"{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:         return f"{v/1_000:.1f}k"
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s

def _delta(cur: Optional[float], prev: Optional[float]) -> Tuple[str, str]:
    if cur is None or prev is None:
        return "—", "—"
    d = cur - prev
    pct = (d / prev * 100.0) if prev else None
    arrow = "▲" if d > 0 else ("▼" if d < 0 else "·")
    d_s   = f"{arrow}{_abbr(abs(d)) if abs(d)>=1000 else ('{:+.2f}'.format(d))}"
    p_s   = "—" if pct is None else ("{:+.2f}".format(pct))
    return d_s, p_s

def _age_label(ts_epoch: Optional[float]) -> str:
    if ts_epoch is None:
        return "(—)"
    try:
        age = time.time() - float(ts_epoch)
        if age < 1: return "(0s)"
        if age < 60: return f"({int(age)}s)"
        return f"({int(age//60)}m)"
    except Exception:
        return "(—)"

def _read_prices_from_db(dl, assets: List[str], cycle_id: Optional[str]) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
    """
    Returns (current_map, previous_map, ts_map)
    Tries DAL first; falls back to raw `sonic_prices`.
    """
    cur_map: Dict[str, float] = {}
    prev_map: Dict[str, float] = {}
    ts_map: Dict[str, float] = {}

    if dl and getattr(dl, "db", None):
        conn = getattr(dl.db, "get_connection", lambda: None)() or getattr(dl.db, "conn", None)
        if conn:
            # Try DAL helpers (Sonic6-style)
            try:
                from backend.core.monitor_core.shared_store import dal  # type: ignore
                # current
                for a, p, ts in dal.latest_prices_with_ts(conn, cycle_id, assets):  # try richer helper
                    if p is not None:
                        cur_map[a] = float(p); ts_map[a] = float(ts) if ts is not None else None
                if not cur_map:
                    for a, p in dal.latest_prices_for_assets(conn, cycle_id, assets):
                        cur_map[a] = float(p); ts_map[a] = None
                # previous
                try:
                    prev_id = dal._prev_cycle_id(conn, cycle_id)  # type: ignore
                except Exception:
                    prev_id = None
                    try:
                        row = conn.execute(
                            "SELECT cycle_id FROM sonic_cycle WHERE started_at < (SELECT started_at FROM sonic_cycle WHERE cycle_id=?) "
                            "ORDER BY started_at DESC LIMIT 1", (cycle_id,)).fetchone()
                        if row: prev_id = row[0]
                    except Exception:
                        prev_id = None
                if prev_id:
                    for a, p in dal.latest_prices_for_assets(conn, prev_id, assets):
                        prev_map[a] = float(p)
            except Exception:
                # Raw fallback: sonic_prices
                try:
                    for a in assets:
                        rows = conn.execute(
                            "SELECT price, ts FROM sonic_prices WHERE asset = ? ORDER BY ts DESC LIMIT 2", (a,)
                        ).fetchall() or []
                        if rows:
                            cur_map[a] = float(rows[0][0]); ts_map[a] = float(rows[0][1]) if rows[0][1] is not None else None
                        if len(rows) > 1:
                            prev_map[a] = float(rows[1][0])
                except Exception:
                    pass
    return cur_map, prev_map, ts_map

def render(csum: Dict[str, Any], *, dl=None) -> None:
    # desired order
    assets = [a for a in ("BTC","ETH","SOL")]

    cur_map: Dict[str, Optional[float]] = {}
    prev_map: Dict[str, Optional[float]] = {}
    ts_map: Dict[str, Optional[float]] = {}

    # DB-first (matches price_monitor)
    db_cur, db_prev, db_ts = _read_prices_from_db(dl, assets, csum.get("cycle_id"))
    cur_map.update(db_cur); prev_map.update(db_prev); ts_map.update(db_ts)

    # fallback to csum if db missing
    if not cur_map and (csum.get("prices_top3") or []):
        for item in csum["prices_top3"]:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                sym, price = str(item[0]).upper(), item[1]
            elif isinstance(item, dict):
                sym = str(item.get("asset") or item.get("symbol") or item.get("market") or "?").upper()
                price = item.get("price") or item.get("current_price")
            else:
                continue
            try:
                cur_map[sym] = float(price) if price is not None else None
            except Exception:
                cur_map[sym] = None

    # order BTC, ETH, SOL then any extras
    order = [s for s in ("BTC","ETH","SOL") if s in cur_map or s in prev_map]
    for s in assets:
        if s not in order:
            order.append(s)

    rows = []
    for sym in order:
        icon = "🟡" if sym == "BTC" else "🔷" if sym == "ETH" else "🟣" if sym == "SOL" else "·"
        cur  = cur_map.get(sym)
        prev = prev_map.get(sym)
        da, dp = _delta(cur, prev)
        checked = _age_label(ts_map.get(sym))
        rows.append([f"{icon} {sym}", _abbr(cur), _abbr(prev), da, dp, checked])

    title = "💰 Prices"
    headers = ["Asset", "Current", "Previous", "Δ", "Δ%", "Checked"]

    if _HAS_RICH and console is not None:
        tbl = Table(show_header=False, show_edge=True, box=BOX, pad_edge=False)
        for _ in headers: tbl.add_column(justify="right")
        tbl.columns[0].justify = "left"
        tbl.add_row(Text(title, style="bold"), "", "", "", "", "", end_section=True)
        tbl.add_row(*[Text(h, style="bold") for h in headers], end_section=True)
        for a,c,p,da,dp,t in rows:
            da_txt = Text(da); dp_txt = Text(dp)
            if da.startswith("▲") or (dp and not dp.startswith("-") and dp not in ("—","")):
                da_txt.stylize("green"); dp_txt.stylize("green")
            elif da.startswith("▼") or (dp and dp.startswith("-")):
                da_txt.stylize("red"); dp_txt.stylize("red")
            tbl.add_row(a,c,p,da_txt,dp_txt,t)
        console.print(tbl)
    else:
        widths = [len(h) for h in headers]
        for r in rows:
            for i, cell in enumerate(r): widths[i] = max(widths[i], len(str(cell)))
        top = "┌" + "┬".join("─"*w for w in widths) + "┐"
        sep = "├" + "┼".join("─"*w for w in widths) + "┤"
        bot = "└" + "┴".join("─"*w for w in widths) + "┘"
        print(top); totalw = sum(widths) + len(widths) - 1
        print("│" + (title + " "*(totalw - len(title))) + "│"); print(sep)
        print("│" + "│".join(str(h).ljust(widths[i]) for i,h in enumerate(headers)) + "│"); print(sep)
        for r in rows:
            print("│" + "│".join(str(r[i]).rjust(widths[i]) if i else str(r[i]).ljust(widths[i]) for i in range(len(headers))) + "│")
        print(bot)
