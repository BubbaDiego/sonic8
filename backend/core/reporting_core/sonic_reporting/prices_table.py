# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import importlib

# optional rich
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

def _age_label(age_s: Optional[float]) -> str:
    if age_s is None: return "(—)"
    try:
        s = float(age_s)
        if s < 1: return "(0s)"
        if s < 60: return f"({int(s)}s)"
        return f"({int(s//60)}m)"
    except Exception:
        return f"({age_s})"

def render(csum: Dict[str, Any], *, dl=None) -> None:
    """
    Build a Prices table using DB helpers:
      - dal.latest_prices_for_assets(conn, cycle_id, assets) for current
      - prev cycle id (DB walker) for previous
      - dal.price_age_for(conn, cycle_id, assets) for ages
    Falls back to csum.prices_top3 if DAL is unavailable.
    """
    # desired order
    assets_env = (csum.get("prices") or {}).get("assets") or ["BTC","ETH","SOL"]
    assets = [str(a).upper() for a in assets_env]

    curr_map: Dict[str, Optional[float]] = {}
    prev_map: Dict[str, Optional[float]] = {}
    ages: Dict[str, Optional[float]] = {}

    if dl and getattr(dl, "db", None):
        try:
            from backend.core.monitor_core.shared_store import dal  # type: ignore
            conn = dl.db.get_connection() if hasattr(dl.db, "get_connection") else dl.db.conn  # best effort
            # current
            for a, p in dal.latest_prices_for_assets(conn, csum.get("cycle_id"), assets):
                curr_map[a] = float(p)
            # ages (per-asset, in seconds)
            ages = dal.price_age_for(conn, csum.get("cycle_id"), assets, lookback=100)
            # prev cycle id and previous prices
            # Walk prev via helper by reusing latest_prices_for_assets on the previous cycle id
            # a small helper exists in Sonic6 dal: _prev_cycle_id; if not exported, compute from sonic_cycle table
            try:
                # direct helper (Sonic6 style)
                prev_id = dal._prev_cycle_id(conn, csum.get("cycle_id"))  # type: ignore
            except Exception:
                prev_id = None
                try:
                    row = conn.execute(
                        "SELECT cycle_id FROM sonic_cycle WHERE started_at < (SELECT started_at FROM sonic_cycle WHERE cycle_id=?) "
                        "ORDER BY started_at DESC LIMIT 1", (csum.get("cycle_id"),)
                    ).fetchone()
                    prev_id = row[0] if row else None
                except Exception:
                    prev_id = None
            if prev_id:
                for a, p in dal.latest_prices_for_assets(conn, prev_id, assets):
                    prev_map[a] = float(p)
        except Exception:
            curr_map = {}
            prev_map = {}
            ages = {}

    # fallback from csum if DB path failed
    if not curr_map and (csum.get("prices_top3") or []):
        for item in csum["prices_top3"]:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                sym, price = str(item[0]).upper(), item[1]
            elif isinstance(item, dict):
                sym = str(item.get("asset") or item.get("symbol") or item.get("market") or "?").upper()
                price = item.get("price") or item.get("current_price")
            else:
                continue
            try:
                curr_map[sym] = float(price) if price is not None else None
            except Exception:
                curr_map[sym] = None

    # order assets (BTC, ETH, SOL first; then others)
    preferred = [s for s in ("BTC","ETH","SOL") if s in (curr_map or {}) or s in (prev_map or {})]
    for s in assets:
        if s not in preferred:
            preferred.append(s)

    rows = []
    for sym in preferred:
        icon = "🟡" if sym == "BTC" else "🔷" if sym == "ETH" else "🟣" if sym == "SOL" else "·"
        cur  = curr_map.get(sym)
        prev = prev_map.get(sym)
        da, dp = _delta(cur, prev)
        checked = _age_label((ages or {}).get(sym))
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
