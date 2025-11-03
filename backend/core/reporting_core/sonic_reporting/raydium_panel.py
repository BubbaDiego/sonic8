"""
Sonic Reporting Panel — Raydium

Minimal console panel to prove end-to-end headless integration:
- Scans wallet for Raydium CLMM position NFTs (via RPC)
- Enriches from Raydium API (pool + prices)
- Prints a compact table with a USD total

USAGE (from sequencer):
    from backend.core.reporting_core.sonic_reporting.raydium_panel import render_raydium_panel
    render_raydium_panel(wallets=[{"name": "VaderWallet", "address": "C9JAHc…"}], rpc_url=os.getenv("RPC_URL"))

Notes:
- No writes, no signing — read-only.
- Dependencies: standard lib + base58 (install if missing).
"""

from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional

from backend.data.dl_raydium import DLRaydium


def _fmt_amt(x: float | None) -> str:
    if not x or x == 0:
        return "—"
    # Human-ish formatting; these amounts can be big because L is big.
    if abs(x) >= 1_000_000:
        return f"{x/1_000_000:.2f}M"
    if abs(x) >= 1_000:
        return f"{x/1_000:.2f}K"
    return f"{x:.4f}"


def _fmt_usd(v: float | None) -> str:
    if v is None:
        return "$—"
    s = abs(v)
    if s >= 1_000_000:
        body = f"{s/1_000_000:.2f}M"
    elif s >= 1_000:
        body = f"{s/1_000:.2f}K"
    else:
        body = f"{s:.2f}"
    sign = "-" if v < 0 else ""
    return f"{sign}${body}"


def render_raydium_panel(
    wallets: List[Dict[str, str]],
    rpc_url: Optional[str] = None,
) -> Dict[str, float]:
    """
    Returns a summary dict with a 'total_usd'.
    Prints a nicely formatted block to the console.

    wallets: list of {"name": "...", "address": "..."}
    """
    print("\n---------------------------  🧪 Raydium Console  ---------------------------")

    total_global = 0.0
    for w in wallets:
        name = w.get("name", "Wallet")
        addr = w.get("address") or w.get("pubkey") or w.get("address58")
        if not addr:
            continue

        dl = DLRaydium(rpc_url=rpc_url)
        pf = dl.get_owner_portfolio(addr)

        # Header row
        print(f"\n  💼  {name}  ({addr})")
        print("  --------------------------------------------------------------------------")
        print("   #  NFT Mint                                Pool                       Range (ticks)           L (liquidity)      amt0          amt1         USD")
        print("  --------------------------------------------------------------------------")

        if not pf.positions:
            print("   0  (no Raydium CLMM positions discovered)")
            continue

        for i, p in enumerate(pf.positions, start=1):
            rng = f"[{p.tick_lower}, {p.tick_upper}]"
            pool = (p.pool_id[:10] + "…" + p.pool_id[-5:]) if len(p.pool_id) > 20 else p.pool_id
            mint = (p.nft_mint[:10] + "…" + p.nft_mint[-5:]) if len(p.nft_mint) > 20 else p.nft_mint

            print(
                f"  {i:>3}  {mint:<38}  {pool:<25}  {rng:<22}  {p.liquidity:<16}  {_fmt_amt(p.amount0):>10}  {_fmt_amt(p.amount1):>10}  {_fmt_usd(p.usd_value):>10}"
            )

        print("  --------------------------------------------------------------------------")
        print(f"  Total (USD) for {name}: {_fmt_usd(pf.total_usd)}")
        total_global += pf.total_usd

    print("\n  ==========================  Grand Total  ============================")
    print(f"  Portfolio Raydium total: {_fmt_usd(total_global)}")
    print("  ====================================================================\n")

    return {"total_usd": total_global}
