# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.data.data_locker import DataLocker
from backend.core.common.wallet_resolver import resolve_active_wallet

IC_HEAD = "🧪"
W_POOL, W_ADDR, W_LP, W_USD, W_APR, W_CHK = 22, 26, 10, 12, 8, 12


def _pad(s: str, n: int, align: str = "left") -> str:
    s = "" if s is None else str(s)
    if len(s) >= n:
        return s[:n]
    pad = " " * (n - len(s))
    return (s + pad) if align == "left" else (pad + s)


def _short_addr(a: Optional[str], left=6, right=6) -> str:
    if not a:
        return "—"
    a = a.strip()
    return a if len(a) <= left + right + 1 else f"{a[:left]}…{a[-right:]}"


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

    name = _coalesce(x.get("name"), x.get("pool"), x.get("pair"), x.get("symbol"), _try_parse_details_name(x), "—")
    # Accept the common fields we persist for NFTs; ensure Address column is never blank.
    addr = _coalesce(x.get("address"), x.get("nft_mint"), x.get("mint"), x.get("lp_mint"), x.get("id"))
    usd  = _coalesce(x.get("usd"), x.get("usd_total"), x.get("value_usd"), x.get("value"))
    bal  = _coalesce(x.get("balance"), x.get("lp_balance"), x.get("amount"))
    apr  = _coalesce(x.get("apr"), x.get("apy"), x.get("apy_7d"), x.get("apr_day"))
    return {"name": name, "address": addr, "usd": (float(usd) if usd is not None else None),
            "balance": (float(bal) if bal is not None else None),
            "apr": (float(apr) if isinstance(apr, (int,float)) else None)}


def render(dl: DataLocker, csum: Any, default_json_path: Optional[str] = None):
    owner = resolve_active_wallet(dl)
    rows: List[Dict[str, Any]] = []

    # Service-first (db-backed)
    rsvc = getattr(dl, "raydium", None)
    if rsvc:
        for name in ("get_by_owner", "get_positions"):
            fn = getattr(rsvc, name, None)
            if callable(fn):
                try:
                    out = fn(owner) if name == "get_by_owner" else fn(owner)  # tolerant sig
                    if isinstance(out, list) and out:
                        rows = [_normalize_row(r) for r in out]
                        break
                except TypeError:
                    try:
                        out = fn()
                        if owner and isinstance(out, list):
                            out = [x for x in out if x.get("owner") == owner]
                        if isinstance(out, list) and out:
                            rows = [_normalize_row(r) for r in out]
                            break
                    except Exception:
                        pass
                except Exception:
                    pass

    print("\n  ---------------------- 🧪  Raydium LPs  ----------------------")
    print(f"  [RAY] source={'dl.raydium' if rows else 'none'} count={len(rows)}")

    if not rows:
        print("  (no raydium positions)")
        return

    now = datetime.now()
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

    tot = 0.0
    for r in rows:
        if isinstance(r.get("usd"), (int, float)):
            tot += float(r["usd"])
        line = (
            "    "
            + _pad(f"{IC_HEAD} {r['name']}", W_POOL)
            + _pad(_short_addr(r["address"]), W_ADDR)
            + _pad(_fmt_int(r["balance"]), W_LP, "right")
            + _pad(_fmt_compact_usd(r["usd"]), W_USD, "right")
            + _pad(f"{r['apr']:.1f}%" if isinstance(r["apr"], (int, float)) else "—", W_APR, "right")
            + _pad(now.strftime("%I:%M%p").lstrip("0").lower(), W_CHK, "right")
        )
        print(line)

    print("    " + _pad("", W_POOL) + _pad("Total (USD):", W_ADDR)
          + _pad("", W_LP, "right") + _pad(_fmt_compact_usd(tot), W_USD, "right")
          + _pad("", W_CHK, "right"))
    print("    " + _pad("", W_POOL) + _pad("Checked:", W_ADDR)
          + _pad("", W_LP, "right") + _pad(now.strftime('%I:%M%p').lstrip('0').lower(), W_USD + W_CHK, "right"))
