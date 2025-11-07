# backend/core/reporting_core/sonic_reporting/raydium_panel.py
# -*- coding: utf-8 -*-
"""
Raydium LPs panel — service-first, no get_manager calls.

Columns:
 • Pool
 • Address
 • LP
 • USD
 • APR
 • Checked
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.data.data_locker import DataLocker

IC_HEAD = "🧪"

# column widths
W_POOL = 22
W_ADDR = 26
W_LP   = 10
W_USD  = 12
W_APR  = 8
W_CHK  = 12


# ── formatting helpers ─────────────────────────────────────────────────────────

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
        return f"{int(float(x)):,}"
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


# ── data shaping ───────────────────────────────────────────────────────────────

def _coalesce(*vals):
    for v in vals:
        if v is not None:
            return v
    return None

def _try_parse_details_name(x: Dict[str, Any]) -> Optional[str]:
    det = x.get("details")
    if isinstance(det, str):
        try:
            det = json.loads(det)
        except Exception:
            det = None
    if isinstance(det, dict):
        pair = det.get("pair") or det.get("pool") or det.get("symbol")
        if isinstance(pair, str) and pair:
            return pair
        a = det.get("mintA") or det.get("tokenA")
        b = det.get("mintB") or det.get("tokenB")
        if isinstance(a, str) and isinstance(b, str):
            return f"{_short_addr(a,4,4)}/{_short_addr(b,4,4)}"
    return None

def _normalize_row(x: Any) -> Dict[str, Any]:
    if not isinstance(x, dict):
        x = getattr(x, "__dict__", {}) or {}

    name = _coalesce(
        x.get("name"),
        x.get("pool"),
        x.get("pair"),
        x.get("symbol"),
        _try_parse_details_name(x),
        "—",
    )
    addr = _coalesce(
        x.get("address"), x.get("mint"), x.get("nft_mint"),
        x.get("lp_mint"), x.get("lpMint"), x.get("id")
    )
    chain = x.get("chain") or "SOL"
    bal = _coalesce(x.get("balance"), x.get("lp_balance"), x.get("amount"), x.get("liquidity"))
    usd = _coalesce(x.get("usd"), x.get("usd_total"), x.get("usd_value"),
                    x.get("value"), x.get("value_usd"), x.get("valuation"))
    apr = _coalesce(x.get("apr"), x.get("apy"), x.get("apy_7d"), x.get("apr_day"))
    checked = _coalesce(x.get("checked_at"), x.get("updated_at"), x.get("ts"), x.get("checked"))

    return {
        "name": name,
        "address": addr,
        "chain": chain if isinstance(chain, str) else "SOL",
        "balance": float(bal) if bal is not None else None,
        "usd": float(usd) if usd is not None else None,
        "apr": float(apr) if isinstance(apr, (int, float)) else None,
        "checked": checked,
    }


# ── service + fallbacks (NO get_manager) ───────────────────────────────────────

def _active_owner(dl: DataLocker) -> Optional[str]:
    sys = getattr(dl, "system", None)
    if sys and hasattr(sys, "get_var"):
        for k in ("wallet.current_pubkey", "wallet_pubkey",
                  "active_wallet_pubkey", "current_wallet_pubkey"):
            try:
                v = sys.get_var(k)
                if isinstance(v, str) and len(v) > 30:
                    return v
            except Exception:
                pass
    return None

def _rows_from_service(dl: DataLocker) -> Optional[tuple[list[dict], str]]:
    mgr = getattr(dl, "raydium", None)
    if not mgr:
        return None
    owner = _active_owner(dl)

    # Try typical service methods without get_manager
    for name, want_owner in (("get_positions", True),
                             ("get_by_owner", True),
                             ("get_positions", False)):
        fn = getattr(mgr, name, None)
        if not callable(fn):
            continue
        try:
            out = fn(owner) if want_owner else fn()
            if isinstance(out, list) and out:
                return ([_normalize_row(o) for o in out], f"service:raydium.{name}({('owner' if want_owner else 'all')})")
        except Exception:
            # swallow; keep trying fallbacks
            pass
    return None

def _read_raydium_positions(dl: DataLocker) -> (List[Dict[str, Any]], str):
    # 0) DB-backed service (dl.raydium) FIRST
    svc = _rows_from_service(dl)
    if svc:
        return svc

    # 1) system var fallback (what the console writes)
    sys = getattr(dl, "system", None)
    if sys and hasattr(sys, "get_var"):
        for key in ("raydium_positions", "raydium_lp_positions", "lp_positions"):
            try:
                arr = sys.get_var(key)
            except Exception:
                arr = None
            if isinstance(arr, list) and arr:
                return ([_normalize_row(x) for x in arr], f"system[{key}]")

    # 2) portfolio/cache stashes if they exist (no hard deps)
    for base in ("portfolio", "cache"):
        node = getattr(dl, base, None)
        if node is None:
            continue
        for name in ("raydium_positions", "lp_positions", "raydium", "raydium_positions_by_wallet"):
            obj = getattr(node, name, None)
            if isinstance(obj, list) and obj:
                return ([_normalize_row(x) for x in obj], f"dl.{base}.{name}")

    return ([], "none")


# ── render ─────────────────────────────────────────────────────────────────────

def render(dl, csum, default_json_path=None):
    rows, source = _read_raydium_positions(dl)
    print("\n  ---------------------- 🧪  Raydium LPs  ----------------------")
    print(f"  [RAY] source={source} count={len(rows)}")

    if not rows:
        print("  (no raydium positions)")
        return

    now = datetime.now()
    rows = [r for r in (_normalize_row(r) for r in rows) if r]
    rows.sort(key=lambda r: (r["usd"] or 0.0), reverse=True)

    header = (
        "    "
        + _pad("Pool",  W_POOL)
        + _pad("Address", W_ADDR)
        + _pad("LP",    W_LP,   "right")
        + _pad("USD",   W_USD,  "right")
        + _pad("APR",   W_APR,  "right")
        + _pad("Checked", W_CHK, "right")
    )
    print(header)

    total_usd = 0.0
    for r in rows:
        if isinstance(r.get("usd"), (int, float)):
            total_usd += float(r["usd"])
        line = (
            "    "
            + _pad(f"{IC_HEAD} {r['name']}", W_POOL)
            + _pad(_short_addr(r["address"]), W_ADDR)
            + _pad(_fmt_int(r["balance"]), W_LP, "right")
            + _pad(_fmt_compact_usd(r["usd"]), W_USD, "right")
            + _pad(f"{r['apr']:.1f}%" if isinstance(r["apr"], (int, float)) else "—", W_APR, "right")
            + _pad(_fmt_time_only(now), W_CHK, "right")
        )
        print(line)

    print(
        "    "
        + _pad("", W_POOL)
        + _pad("Total (USD):", W_ADDR)
        + _pad("", W_LP, "right")
        + _pad(_fmt_compact_usd(total_usd), W_USD, "right")
        + _pad("", W_CHK, "right")
    )
    print(
        "    "
        + _pad("", W_POOL)
        + _pad("Checked:", W_ADDR)
        + _pad("", W_LP, "right")
        + _pad(_fmt_time_date(now), W_USD + W_CHK, "right")
    )
