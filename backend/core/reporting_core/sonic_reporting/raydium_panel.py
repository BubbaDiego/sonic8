# -*- coding: utf-8 -*-
"""
Raydium LPs panel — always prints, robust data discovery.

Columns:
 • Pool (name with icon)
 • Address (shortened)
 • LP (integer, right aligned)
 • USD (compact: 280.8k / 1.2m, right aligned)
 • APR (if available)
 • Checked (time only '1:05pm')

Footer:
 • 'Total (USD):' compact sum of USD
 • 'Checked:' with local '1:05pm - 11/2/25'

Data discovery order:
 1) dl.read_raydium_positions()   # if your manager exposes it
 2) dl.raydium.get_positions()    # or dl.raydium.positions
 3) dl.portfolio.raydium_positions
 4) dl.system['raydium_positions'] / ['raydium_lp_positions'] / ['lp_positions']
 5) empty list fallback (prints '(no raydium positions)')

Each path logs its source for visibility.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.data.data_locker import DataLocker
from backend.core.logging import log

IC_HEAD = "🧪"
CHAIN_ICON = {"SOL": "🟣", "ETH": "🔷", "BTC": "🟡"}

# column widths
W_POOL   = 22       # 'Pool' (with icon)
W_ADDR   = 26       # Address shown as short form
W_LP     = 10       # right aligned integer
W_USD    = 12       # right aligned compact USD
W_APR    = 8        # right aligned '12.3%' or '—'
W_CHK    = 12       # right aligned time (hh:mmam)


def _pad(s: str, n: int, align: str = "left") -> str:
    s = "" if s is None else str(s)
    if len(s) >= n:
        return s[:n]
    pad = " " * (n - len(s))
    return (s + pad) if align == "left" else (pad + s)


def _short_addr(addr: Optional[str], left: int = 6, right: int = 6) -> str:
    if not addr:
        return "—"
    a = addr.strip()
    if len(a) <= left + right + 1:
        return a
    return f"{a[:left]}…{a[-right:]}"


def _fmt_int(x: Optional[float]) -> str:
    if x is None:
        return "—"
    try:
        v = int(float(x))
        return f"{v:,}"
    except Exception:
        return "—"


def _fmt_compact_usd(x: Optional[float]) -> str:
    if x is None:
        return "—"
    try:
        v = float(x)
        sign = "-" if v < 0 else ""
        v = abs(v)
        if v >= 1_000_000_000:
            return f"{sign}${v/1_000_000_000:.1f}b".replace(".0b", "b")
        if v >= 1_000_000:
            return f"{sign}${v/1_000_000:.1f}m".replace(".0m", "m")
        if v >= 1_000:
            return f"{sign}${v/1_000:.1f}k".replace(".0k", "k")
        return f"{sign}${v:,.0f}"
    except Exception:
        return "—"


def _fmt_time_only(dt: Optional[datetime] = None) -> str:
    try:
        d = dt or datetime.now()
        return d.strftime("%I:%M%p").lstrip("0").lower()
    except Exception:
        return "(now)"


def _fmt_time_date(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now()
    t = d.strftime("%I:%M%p").lstrip("0").lower()
    return f"{t} - {d.month}/{d.day}/{str(d.year)[-2:]}"
                               # correct slice     ^^^^


def _coalesce(*vals):
    for v in vals:
        if v is not None:
            return v
    return None


def _read_raydium_positions(dl: DataLocker) -> (List[Dict[str, Any]], str):
    """
    Return (rows, source_label). Each row contains:
      name, address, chain, balance, usd, apr, checked(optional)
    """
    # 1) Manager-style
    for attr in ("read_raydium_positions", "get_raydium_positions"):
        fn = getattr(dl, attr, None)
        if callable(fn):
            try:
                items = fn() or []
                if items:
                    return [_normalize_row(x) for x in items if x], f"manager:{attr}"
            except Exception as e:
                log.warning(f"[RAY] manager call {attr} failed: {e}")

    # 2) dl.raydium.*
    try:
        r = getattr(dl, "raydum", None) or getattr(dl, "raydium", None)
        if r is not None:
            for attr in ("positions", "lp_positions", "get_positions", "get_lp_positions"):
                obj = getattr(r, attr, None)
                if callable(obj):
                    try:
                        out = obj()
                    except Exception:
                        out = None
                else:
                    out = obj
                if isinstance(out, list) and out:
                    return ([_normalize_row(x) for x in out if x], f"dl.raydium.{attr}")
    except Exception as e:
        log.warning(f"[RAY] dl.raydium* read failed: {e}")

    # 3) dl.portfolio / dl.cache stash
    for base in ("portfolio", "cache"):
        try:
            node = getattr(dl, base, None)
            if node is None:
                continue
            for name in ("raydium_positions", "lp_positions", "raydium", "raydium_positions_by_wallet"):
                obj = getattr(node, name, None)
                if isinstance(obj, list) and obj:
                    return ([_normalize_row(x) for x in obj if x], f"dl.{base}.{name}")
        except Exception as e:
            log.warning(f"[RAY] dl.{base} read failed: {e}")

    # 4) system var fallback
    for key in ("raydium_positions", "raydium_lp_positions", "lp_positions"):
        try:
            arr = (dl.system.get_var(key) if getattr(dl, "system", None) else None) or []
            if isinstance(arr, list) and arr:
                return ([_normalize_row(x) for x in arr if x], f"system[{key}]")
        except Exception as e:
            log.warning(f"[RAY] system var {key} read failed: {e}")

    return ([], "none")


def _normalize_row(x: Any) -> Dict[str, Any]:
    """
    Best-effort field mapping from diverse upstream shapes to:
      name, address, chain, balance, usd, apr, checked
    """
    if not isinstance(x, dict):
        x = getattr(x, "__dict__", {}) or {}

    name = _coalesce(x.get("name"), x.get("pool"), x.get("pair"), x.get("symbol"))
    addr = _coalesce(x.get("address"), x.get("mint"), x.get("lp_mint"), x.get("lpMint"), x.get("id"))
    chain = _coalesce(x.get("chain"), "SOL")

    # numeric values (balance & usd)
    bal = _coalesce(x.get("balance"), x.get("lp_balance"), x.get("amount"), x.get("liquidity"))
    usd = _coalesce(x.get("usd"), x.get("usd_value"), x.get("value"), x.get("value_usd"), x.get("valuation"))
    apr = _coalesce(x.get("apr"), x.get("apy"), x.get("apy_7d"), x.get("apr_day"), x.get("apy_7day"))
    # optional timestamp
    checked = _coalesce(x.get("checked_at"), x.get("updated_at"), x.get("ts"))

    return {
        "name": name or "—",
        "address": addr,
        "chain": chain if isinstance(chain, str) else "SOL",
        "balance": float(bal) if bal is not None else None,
        "usd": float(usd) if usd is not None else None,
        "apr": float(apr) if isinstance(apr, (int, float)) else None,
        "checked": checked,
    }


def render(dl, csum, default_json_path=None):
    rows, source = _read_raydium_positions(dl)
    print("\n  ---------------------- 🧪  Raydium LPs  ----------------------")
    print(f"  [RAY] source={source} count={len(rows)}")

    if not rows:
        print("  (no raydium positions)")
        return

    # Sort by USD descending
    now = datetime.now()
    rows = [r for r in (_normalize_row(r) for r in rows) if r]
    rows.sort(key=lambda r: (r["usd"] or 0.0), reverse=True)

    # Header
    header = (
        "    "
        + _pad("Pool",  W_NAME := 22)
        + _pad("Address", W_ADDR)
        + _pad("LP",    W_LP,   "right")
        + _pad("USD",   W_USD,  "right")
        + _pad("APR",   W_APR,  "right")
        + _pad("Checked", W_CHECK := 12, "right")
    )
    print(header)

    total_usd = 0.0
    for r in rows:
        pool = f"{IC_HEAD} {r['name']}"
        chain = r["chain"]
        # If you prefer to show the chain icon somewhere, uncomment:
        # pool = f"{CHAIN_ICON.get(chain, '▫️')} {r['name']}"

        usd = r["usd"]
        if isinstance(usd, (int, float)):
            total_usd += float(usd)

        line = (
            "    "
            + _pad(pool, W_NAME)
            + _pad(_short_addr(r["address"]), W_ADDR)
            + _pad(_fmt_int(r["balance"]), W_LP, "right")
            + _pad(_fmt_compact_usd(r["usd"]), W_USD, "right")
            + _pad(f"{r['apr']:.1f}%" if isinstance(r["apr"], (int, float)) else "—", W_APR, "right")
            + _pad(_fmt_time_only(now), W_CHECK, "right")
        )
        print(line)

    # Footer with total USD (compact)
    print(
        "    "
        + _pad("", W_NAME)
        + _pad("Total (USD):", W_ADDR)
        + _pad("", W_LP, "right")
        + _pad(_fmt_compact_usd(total_usd), W_USD, "right")
        + _pad("", W_CHECK, "right")
    )
    print(
        "    "
        + _pad("", W_NAME)
        + _pad("Checked:", W_ADDR)
        + _pad("", W_LP, "right")
        + _pad(_fmt_time_date(now), W_USD + W_CHECK, "right")
    )
