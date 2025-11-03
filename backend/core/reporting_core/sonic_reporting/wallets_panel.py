# -*- coding: utf-8 -*-
"""
Wallets panel — final polish
 • Header icon: 💼  • Per-row icon: 💳
 • Chain shows icon + chain (🟣 SOL / 🔷 ETH / 🟡 BTC)
 • Address width tightened; Balance/Usd right-aligned and compact
 • Balance: $#,### (integer) — USD: compact (K/M/B) without $
 • Totals row shows Balance total (if single-chain) and USD total, colored
 • Checked per row: time only; footer: time - date
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from datetime import datetime
from backend.data.data_locker import DataLocker
from backend.core.logging import log

IC_HEADER = "💼"   # header icon
IC_ROW    = "💳"   # per-row icon
CHAIN_ICON = {"SOL": "🟣", "ETH": "🔷", "BTC": "🟡"}

# Column widths (tightened Address so the gap shrinks)
W_NAME  = 18
W_CHAIN = 8
W_ADDR  = 22   # reduced from 26
W_BAL   = 14   # right
W_USD   = 12   # right
W_CHECK = 12   # right

# ANSI color for totals (bright cyan); reset at end
CLR_TOT = "\x1b[96m"
CLR_RST = "\x1b[0m"


# ---------------- formatting helpers ----------------
def _pad(s: str, n: int, align: str = "left") -> str:
    s = "" if s is None else str(s)
    return s[:n] if len(s) >= n else (s + " " * (n - len(s)) if align == "left" else " " * (n - len(s)) + s)

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
        return f"${v:,}"         # Balance shows $ and integer
    except Exception:
        return "—"

def _fmt_compact_usd_no_dollar(x: Optional[float]) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    try:
        v = abs(float(x))
        sign = "-" if float(x) < 0 else ""
        if v >= 1_000_000_000: return f"{sign}{v/1_000_000_000:.1f}B".replace(".0B", "B")
        if v >= 1_000_000:     return f"{sign}{v/1_000_000:.1f}M".replace(".0M", "M")
        if v >= 1_000:         return f"{sign}{v/1_000:.1f}K".replace(".0K", "K")
        return f"{sign}{v:,.0f}"
    except Exception:
        return "—"

def _fmt_time_only(dt: Optional[datetime] = None) -> str:
    try:
        d = dt or datetime.now()
        return d.strftime("%I:%M%p").lstrip("0").lower()  # '2:05pm'
    except Exception:
        return "(now)"

def _fmt_time_date(dt: Optional[datetime] = None) -> str:
    try:
        d = dt or datetime.now()
        tpart = d.strftime("%I:%M%p").lstrip("0").lower()
        dpart = f"{d.month}/{d.day}/{str(d.year)[-2:]}"
        return f"{tpart} - {dpart}"
    except Exception:
        return "(now)"


# ---------------- data helpers ----------------
def _price_usd(dl: DataLocker, chain: str) -> Optional[float]:
    sym = {"SOL": "SOL", "ETH": "ETH", "BTC": "BTC"}.get(chain)
    if not sym: return None
    try:
        info = dl.get_latest_price(sym) or {}
        p = info.get("current_price")
        return float(p) if p is not None else None
    except Exception:
        return None

def _read_wallets(dl: DataLocker) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        for w in (dl.read_wallets() or []):
            name = w.get("name")
            addr = w.get("public_address") or w.get("address")
            bal  = w.get("balance")
            rows.append({"name": name, "address": addr, "balance": bal})
        return rows
    except Exception as e:
        log.warning(f"[WALLETS] manager read failed, falling back: {e}", source="wallets_panel")

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


# ---------------- renderer ----------------
def render(dl: DataLocker, csum=None, default_json_path: str | None = None, **_kwargs) -> None:
    try:
        wallets = _read_wallets(dl)
    except Exception as e:
        log.error(f"[WALLETS] render read failed: {e}", source="wallets_panel")
        wallets = []

    print(f"\n  ---------------------- {IC_HEADER}  Wallets  ----------------------")
    if not wallets:
        print("  (no wallets)")
        return

    # Header
    header = (
        "    "
        + _pad("Name", W_NAME)
        + _pad("Chain", W_CHAIN)
        + _pad("Address", W_ADDR)
        + _pad("Balance", W_BAL, "right")
        + _pad("USD", W_USD, "right")
        + _pad("Checked", W_CHECK, "right")
    )
    print(header)

    total_usd = 0.0
    have_usd = False
    total_balance: Optional[float] = 0.0
    chain_set = set()
    now = datetime.now()

    for w in wallets:
        name = str(w.get("name") or "—")
        addr = w.get("address")
        chain = _guess_chain(addr)
        chain_set.add(chain)

        icon = CHAIN_ICON.get(chain, "▫️")
        bal = w.get("balance")

        px = _price_usd(dl, chain)
        usd = (float(bal) * float(px)) if (bal not in (None, "") and px is not None) else None
        if usd is not None:
            have_usd = True
            total_usd += float(usd)

        try:
            if bal not in (None, ""):
                total_balance = (total_balance or 0.0) + float(bal)
        except Exception:
            pass

        name_cell  = f"{IC_ROW} {name}"
        chain_cell = f"{icon} {chain}"

        line = (
            "    "
            + _pad(name_cell, W_NAME)
            + _pad(chain_cell, W_CHAIN)
            + _pad(_short_addr(addr), W_ADDR)
            + _pad(_fmt_int_balance(bal), W_BAL, "right")
            + _pad(_fmt_compact_usd_no_dollar(usd), W_USD, "right")
            + _pad(_fmt_time_only(now), W_CHECK, "right")
        )
        print(line)

    # Totals (colored). Only show Balance total if all wallets are same chain.
    one_chain = (len(chain_set) == 1)
    bal_total_cell = _fmt_int_balance(total_balance) if one_chain else ""

    total_line = (
        "    "
        + _pad("", W_NAME)
        + _pad("", W_CHAIN)
        + _pad("Total (USD):", W_ADDR)
        + _pad(bal_total_cell, W_BAL, "right")
        + _pad(_fmt_compact_usd_no_dollar(total_usd) if have_usd else "—", W_USD, "right")
        + _pad("", W_CHECK, "right")
    )
    print(CLR_TOT + total_line + CLR_RST)

    checked_footer = (
        "    "
        + _pad("", W_NAME)
        + _pad("", W_CHAIN)
        + _pad("Checked:", W_ADDR)
        + _pad("", W_BAL, "right")
        + _pad(_fmt_time_date(now), W_USD + W_CHECK, "right")
    )
    print(checked_footer)
