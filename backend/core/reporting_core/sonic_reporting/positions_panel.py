# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.data.data_locker import DataLocker
from backend.core.common.wallet_resolver import resolve_active_wallet

IC = "📊"
W_ASSET, W_SIDE, W_OWNER, W_VAL, W_PNL, W_MISC = 10, 6, 26, 12, 12, 18


def _pad(s: str, n: int, align: str = "left") -> str:
    s = "" if s is None else str(s)
    if len(s) >= n:
        return s[:n]
    pad = " " * (n - len(s))
    return (s + pad) if align == "left" else (pad + s)


def _short(addr: Optional[str], l=6, r=6) -> str:
    if not addr:
        return "—"
    a = addr.strip()
    return a if len(a) <= l + r + 1 else f"{a[:l]}…{a[-r:]}"


def _fmt_usd(v: Optional[float]) -> str:
    if v is None:
        return "—"
    try:
        n = float(v)
        sign = "-" if n < 0 else ""
        n = abs(n)
        if n >= 1_000_000_000:
            return f"{sign}${n/1_000_000_000:.1f}b".replace(".0b", "b")
        if n >= 1_000_000:
            return f"{sign}${n/1_000_000:.1f}m".replace(".0m", "m")
        if n >= 1_000:
            return f"{sign}${n/1_000:.1f}k".replace(".0k", "k")
        return f"{sign}${n:,.0f}"
    except Exception:
        return "—"


def _normalize_row(x: Any) -> Dict[str, Any]:
    if not isinstance(x, dict):
        x = getattr(x, "__dict__", {}) or {}
    # 'owner' should be a wallet public address (NOT system var)
    return {
        "asset": x.get("asset") or x.get("symbol") or x.get("token"),
        "side": x.get("side") or x.get("direction") or "—",
        "owner": x.get("owner") or x.get("wallet") or x.get("account"),
        "value": x.get("value_usd") or x.get("usd") or x.get("value") or 0.0,
        "pnl": x.get("pnl_usd") or x.get("pnl") or 0.0,
        "lev": x.get("leverage") or x.get("lev"),
        "liq": x.get("liq_price") or x.get("liquidation") or x.get("liq"),
        "misc": x.get("misc") or "",
    }


def _read_positions(dl: DataLocker, owner: Optional[str]) -> List[Dict[str, Any]]:
    pmgr = getattr(dl, "positions", None)
    if pmgr:
        # try by-owner API first
        for name in ("get_by_owner", "get_positions"):
            fn = getattr(pmgr, name, None)
            if callable(fn):
                try:
                    out = fn(owner) if name == "get_by_owner" else fn(owner)  # tolerant sig
                    if isinstance(out, list) and out:
                        rows = [_normalize_row(r) for r in out]
                        return rows
                except TypeError:
                    try:
                        out = fn()
                        if owner and isinstance(out, list):
                            out = [r for r in out if r.get("owner") == owner]
                        if isinstance(out, list) and out:
                            return [_normalize_row(r) for r in out]
                    except Exception:
                        pass
                except Exception:
                    pass
    # Avoid system-var fallbacks for wallet; DB is canonical now.
    return []


def render(dl: DataLocker, csum: Any, default_json_path: Optional[str] = None):
    owner = resolve_active_wallet(dl)
    rows = _read_positions(dl, owner)

    print("\n  ---------------------- 📊  Positions  -----------------------")
    src_label = "dl.positions" if rows else "none"
    print(f"  [POSITIONS] source: {src_label} ({len(rows)} rows)")

    if not rows:
        print("  (no positions)")
        return

    rows.sort(key=lambda r: float(r.get("value") or 0.0), reverse=True)

    # Header
    header = (
        "    "
        + _pad("Asset", W_ASSET)
        + _pad("Side", W_SIDE)
        + _pad("Owner", W_OWNER)
        + _pad("Value", W_VAL, "right")
        + _pad("PnL", W_PNL, "right")
        + _pad("Misc", W_MISC)
    )
    print(header)

    total_val = 0.0
    total_pnl = 0.0

    for r in rows:
        val = float(r.get("value") or 0.0)
        pnl = float(r.get("pnl") or 0.0)
        total_val += val
        total_pnl += pnl

        line = (
            "    "
            + _pad(r.get("asset") or "—", W_ASSET)
            + _pad(str(r.get("side") or "—"), W_SIDE)
            + _pad(_short(r.get("owner")), W_OWNER)
            + _pad(_fmt_usd(val), W_VAL, "right")
            + _pad(_fmt_usd(pnl), W_PNL, "right")
            + _pad(str(r.get("misc") or ""), W_MISC)
        )
        print(line)

    now = datetime.now()
    print(
        "    "
        + _pad("", W_ASSET + W_SIDE)
        + _pad("Totals:", W_OWNER)
        + _pad(_fmt_usd(total_val), W_VAL, "right")
        + _pad(_fmt_usd(total_pnl), W_PNL, "right")
        + _pad(now.strftime("%I:%M%p").lstrip("0").lower(), W_MISC)
    )
