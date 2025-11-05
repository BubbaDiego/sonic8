# -*- coding: utf-8 -*-
from __future__ import annotations
"""
wallets_panel — DL-sourced wallets with a Rich bordered table

Panel-local options (tweak here; no sequencer changes needed):
  WALLET_BORDER = "light" | "none"
  TITLE_COLOR   = <rich color>   (e.g., "bright_cyan")
  BORDER_COLOR  = <rich color>   (e.g., "bright_black")

Signature (lean sequencer):
  render(dl, csum, default_json_path=None)

Behavior:
  • Reads wallets directly from DataLocker (manager first, then DB fallback).
  • Per-row shows: Name / Chain / Address / Balance / USD / Checked
  • Balance is integer dollars with $, USD is compact without $ (K/M/B).
  • Totals row prints USD sum and Balance total only if all wallets share the same chain.
  • Breadcrumb prints the effective source used.
"""

from typing import Any, Dict, List, Optional
import math
from datetime import datetime

# Panel-local UI options
WALLET_BORDER = "light"          # "light" | "none"
TITLE_COLOR   = "bright_cyan"    # Rich color
BORDER_COLOR  = "bright_black"   # Rich color

IC_HEADER = "💼"
IC_ROW    = "💳"
CHAIN_ICON = {"SOL": "🟣", "ETH": "🔷", "BTC": "🟡"}

from backend.data.data_locker import DataLocker
from backend.core.logging import log


# ------------- helpers -------------

def _ensure_dl(dl: Optional[DataLocker]) -> DataLocker:
    if dl is not None:
        return dl
    try:
        return DataLocker.get_instance(r"C:\sonic7\backend\mother.db")
    except Exception:
        return DataLocker.get_instance()

def _short_addr(addr: Optional[str], left: int = 6, right: int = 6) -> str:
    if not addr:
        return "—"
    a = addr.strip()
    return a if len(a) <= left + right + 1 else f"{a[:left]}…{a[-right:]}"

def _guess_chain(addr: Optional[str]) -> str:
    if not addr:
        return "SOL"
    a = addr.strip().lower()
    if a.startswith("0x") and len(a) == 42: return "ETH"
    if a.startswith("bc1") or a[:1] in {"1", "3"}: return "BTC"
    return "SOL"

def _fmt_int_balance(x: Optional[float]) -> str:
    if x is None: return "—"
    try:
        v = int(float(x))
        return f"${v:,}"
    except Exception:
        return "—"

def _fmt_usd_compact(x: Optional[float]) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    v = float(x)
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000_000: return f"{sign}{a/1_000_000_000:.1f}B".replace(".0B", "B")
    if a >= 1_000_000:     return f"{sign}{a/1_000_000:.1f}M".replace(".0M", "M")
    if a >= 1_000:         return f"{sign}{a/1_000:.1f}K".replace(".0K", "K")
    return f"{sign}{a:,.0f}"

def _fmt_time_only(dt: Optional[datetime] = None) -> str:
    try:
        d = dt or datetime.now()
        return d.strftime("%I:%M%p").lstrip("0").lower()
    except Exception:
        return "(now)"


# ------------- DL readers -------------

def _price_usd(dl: DataLocker, chain: str) -> Optional[float]:
    sym = {"SOL": "SOL", "ETH": "ETH", "BTC": "BTC"}.get(chain)
    if not sym:
        return None
    try:
        info = dl.get_latest_price(sym) or {}
        p = info.get("current_price")
        return float(p) if p is not None else None
    except Exception:
        return None

def _read_wallets_via_manager(dl: DataLocker) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        for w in (dl.read_wallets() or []):
            name = w.get("name")
            addr = w.get("public_address") or w.get("address")
            bal  = w.get("balance")
            rows.append({"name": name, "address": addr, "balance": bal})
    except Exception as e:
        log.warning(f"[WALLETS] manager read failed: {e}", source="wallets_panel")
    return rows

def _read_wallets_via_db(dl: DataLocker) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        cur = dl.db.get_cursor()
        if not cur: return rows
        cur.execute("PRAGMA table_info(wallets)")
        cols = {r[1] for r in cur.fetchall()}
        if "name" in cols and "public_address" in cols:
            cur.execute("SELECT name, public_address, COALESCE(balance, 0.0) FROM wallets")
            for name, addr, bal in cur.fetchall():
                rows.append({"name": name, "address": addr, "balance": bal})
        elif "name" in cols and "address" in cols:
            cur.execute("SELECT name, address FROM wallets")
            for name, addr in cur.fetchall():
                rows.append({"name": name, "address": addr, "balance": None})
    except Exception as e:
        log.error(f"[WALLETS] fallback query failed: {e}", source="wallets_panel")
    return rows


# ------------- Rich rendering -------------

def _render_bordered(rows: list[list[str]], header: list[str], title: str) -> None:
    try:
        from rich.table import Table
        from rich.console import Console
        from rich.box import SIMPLE
    except Exception:
        _render_unbordered(rows, header, title)
        return

    table = Table(
        title=f"[{TITLE_COLOR}]{title}[/{TITLE_COLOR}]",
        show_header=True,
        header_style="bold",
        box=SIMPLE,
        border_style=BORDER_COLOR,
        title_justify="left",
        show_edge=True,
        show_lines=False,
        expand=False,
        pad_edge=False,
    )
    for col in header:
        table.add_column(col)

    for r in rows:
        table.add_row(*[str(c) for c in r])

    Console().print(table)

def _render_unbordered(rows: list[list[str]], header: list[str], title: str) -> None:
    print(f"\n  {title}\n")
    widths = [max(len(str(header[c])), max(len(str(r[c])) for r in rows) if rows else 0)
              for c in range(len(header))]
    print("  " + "  ".join(str(header[c]).ljust(widths[c]) for c in range(len(header))))
    print("")
    for r in rows:
        print("  " + "  ".join(str(r[c]).ljust(widths[c]) for c in range(len(header))))


# ------------- panel entry -------------

def render(dl, csum, default_json_path=None):
    dl = _ensure_dl(dl)

    wallets = _read_wallets_via_manager(dl)
    source = "dl.read_wallets"
    if not wallets:
        wallets = _read_wallets_via_db(dl)
        source = "db.wallets"

    title  = f"{IC_HEADER} Wallets"
    header = ["Name", "Chain", "Address", "Balance", "USD", "Checked"]
    out: list[list[str]] = []

    total_usd = 0.0
    have_usd  = False
    total_bal: Optional[float] = 0.0
    chains = set()
    now = datetime.now()

    for w in wallets:
        name = str(w.get("name") or "—")
        addr = w.get("address")
        chain = _guess_chain(addr)
        chains.add(chain)
        icon  = CHAIN_ICON.get(chain, "▫️")

        bal = w.get("balance")
        px  = _price_usd(dl, chain)
        usd = (float(bal) * float(px)) if (bal not in (None, "") and px is not None) else None
        if usd is not None:
            have_usd = True
            total_usd += float(usd)
        try:
            if bal not in (None, ""):
                total_bal = (total_bal or 0.0) + float(bal)
        except Exception:
            pass

        row = [
            f"{IC_ROW} {name}",
            f"{icon} {chain}",
            _short_addr(addr),
            _fmt_int_balance(bal),
            _fmt_usd_compact(usd),
            _fmt_time_only(now),
        ]
        out.append(row)

    # Totals row
    one_chain = (len(chains) == 1)
    bal_total_cell = _fmt_int_balance(total_bal) if one_chain else "—"
    out.append([
        "", "", "Total (USD):",
        bal_total_cell,
        _fmt_usd_compact(total_usd) if have_usd else "—",
        "",
    ])

    if WALLET_BORDER == "light":
        _render_bordered(out, header, title)
    else:
        _render_unbordered(out, header, title)

    print(f"\n[WALLETS] source: {source} ({len(wallets)} rows)")
