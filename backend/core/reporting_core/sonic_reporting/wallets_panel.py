from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from backend.data.data_locker import DataLocker
from backend.core.logging import log

# Minimal inline formatting helpers so we don’t fight the rest of the console code.
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


CHAIN_ICON = {"SOL": "🟣", "ETH": "🔷", "BTC": "🟡"}


def _guess_chain(addr: Optional[str]) -> str:
    if not addr:
        return "SOL"
    a = addr.strip().lower()
    if a.startswith("0x") and len(a) == 42:
        return "ETH"
    if a.startswith("bc1") or a[:1] in {"1", "3"}:
        return "BTC"
    return "SOL"


def _price_usd(dl: DataLocker, chain: str) -> Optional[float]:
    """Read last cached price for SOL/ETH/BTC via DataLocker (safe method)."""
    sym = {"SOL": "SOL", "ETH": "ETH", "BTC": "BTC"}.get(chain)
    if not sym:
        return None
    try:
        info = dl.get_latest_price(sym) or {}
        p = info.get("current_price")
        return float(p) if p is not None else None
    except Exception:
        return None


def _fmt_money(x: Optional[float]) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    try:
        return f"${x:,.2f}"
    except Exception:
        return "—"


def _fmt_qty(x: Optional[float]) -> str:
    if x is None:
        return "—"
    try:
        return f"{x:,.4f}".rstrip("0").rstrip(".")
    except Exception:
        return "—"


def _read_wallets(dl: DataLocker) -> List[Dict[str, Any]]:
    """
    Canonical read path: DataLocker.read_wallets() → DLWalletManager.get_wallets().
    Falls back to direct SQL with (name, public_address, balance) if manager is absent.
    """
    rows: List[Dict[str, Any]] = []
    # Primary path through the manager (preferred). :contentReference[oaicite:2]{index=2}
    try:
        for w in (dl.read_wallets() or []):
            # The wallet rows in this codebase use 'name' and 'public_address'. :contentReference[oaicite:3]{index=3}
            name = w.get("name")
            addr = w.get("public_address") or w.get("address")
            bal = w.get("balance")
            rows.append({"name": name, "address": addr, "balance": bal})
        return rows
    except Exception as e:
        log.warning(f"[WALLETS] manager read failed, falling back: {e}", source="wallets_panel")

    # Defensive fallback: tiny direct query, schema-relaxed.
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return rows
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


def render(dl: DataLocker, **_kwargs) -> None:
    """
    Console renderer. Prints a compact table with Name, Chain, Address, Balance, USD, Checked.
    Never throws; logs loudly if anything misbehaves.
    """
    try:
        wallets = _read_wallets(dl)
    except Exception as e:  # ultra-defensive
        log.error(f"[WALLETS] render read failed: {e}", source="wallets_panel")
        wallets = []

    print("\n  ---------------------- 💳  Wallets  ----------------------")
    if not wallets:
        print("  (no wallets)")
        return

    # Header
    header = (
        "    "
        + _pad("Name", 16)
        + _pad("Chain", 8)
        + _pad("Address", 26)
        + _pad("Balance", 14, "right")
        + _pad("USD", 14, "right")
        + _pad("Checked", 10, "right")
    )
    print(header)

    total_usd = 0.0
    have_usd = False
    now_ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for w in wallets:
        name = str(w.get("name") or "—")
        addr = w.get("address")
        chain = _guess_chain(addr)
        icon = CHAIN_ICON.get(chain, "▫️")
        bal = w.get("balance")
        px = _price_usd(dl, chain)
        usd = (float(bal) * float(px)) if (bal not in (None, "") and px is not None) else None
        if usd is not None:
            have_usd = True
            total_usd += float(usd)

        line = (
            "    "
            + _pad(f"{icon} {name}", 16)
            + _pad(chain, 8)
            + _pad(_short_addr(addr), 26)
            + _pad(_fmt_qty(bal), 14, "right")
            + _pad(_fmt_money(usd), 14, "right")
            + _pad("(now)", 10, "right")
        )
        print(line)

    # Totals footer
    if have_usd:
        print("    " + _pad("", 16) + _pad("", 8) + _pad("Total (USD):", 26) + _pad(_fmt_money(total_usd), 14, "right"))
    print(f"    " + _pad("", 16) + _pad("", 8) + _pad("Checked:", 26) + _pad(now_ts, 14, "right"))
