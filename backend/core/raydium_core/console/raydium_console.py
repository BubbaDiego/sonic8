# -*- coding: utf-8 -*-
"""
Raydium Core — pick-list console (wallet + NFTs)
- Uses project-root signer.txt via backend.services.signer_loader
- RPC comes from RPC_URL or backend.config.rpc.helius_url
- NFT heuristic: token accounts with amount == 1 and decimals == 0

Run:
  py backend/core/raydium_core/console/raydium_console.py
"""

from __future__ import annotations

import os
import sys
import time
from typing import List, Tuple

# UTF-8 out on Windows
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# --- project services (use your existing wiring) ---
from backend.services.signer_loader import load_signer  # finds signer.txt at repo root by default  ✅
from backend.config import rpc as rpc_cfg  # helius_url(), redacted()

# We’ll use solana-py + solders like the rest of your stack
from solders.pubkey import Pubkey
from solana.rpc.api import Client as SolClient
from solana.rpc.types import TokenAccountOpts


def _resolve_rpc_url() -> str:
    """
    Same spirit as backend/services/jupiter_swap.py:
      RPC_URL env takes precedence, else Helius URL helper.
    """
    env = os.getenv("RPC_URL", "").strip()
    if env:
        return env
    try:
        return rpc_cfg.helius_url()  # requires HELIUS_API_KEY set
    except Exception:
        # No Helius key? fall back to public
        return "https://api.mainnet-beta.solana.com"


# ---------- Pretty UI ----------

def banner(title: str, subtitle: str = "") -> None:
    line = "─" * max(18, len(title) + 2)
    print(f"\n╭{line}╮")
    print(f"│ {title} │")
    if subtitle:
        print(f"│ {subtitle} │")
    print(f"╰{line}╯")


def ask(prompt: str, default: str = "") -> str:
    s = input(f"{prompt} [{default}]: ").strip()
    return s or default


def pause():
    input("\n↩️  Enter to continue...")


# ---------- Core ops ----------

def show_wallet(cl: SolClient) -> Pubkey:
    """Load wallet via your signer loader and print pubkey."""
    w = load_signer()  # honors SONIC_SIGNER_PATH and root signer.txt
    pub = w.pubkey()
    print(f"\n🔐 Wallet loaded: {pub}")
    try:
        bal = cl.get_balance(pub).value  # lamports
    except Exception:
        # legacy dict-style fallback
        bal = int((cl.get_balance(pub) or {}).get("result", {}).get("value", 0))
    sol = float(bal) / 1e9
    print(f"   • Balance: {sol:.6f} SOL")
    return pub


def _get_all_token_accounts(cl: SolClient, owner: Pubkey) -> List[str]:
    """Return token-account pubkeys for the owner (all SPL accounts)."""
    resp = cl.get_token_accounts_by_owner(owner, TokenAccountOpts(program_id="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
    try:
        return [str(a.pubkey) for a in resp.value]  # new API object form
    except Exception:
        return [a["pubkey"] for a in resp["result"]["value"]]  # legacy dict form


def _token_balance_decimals(cl: SolClient, token_acc: str) -> Tuple[int, int]:
    """
    Return (amount_raw, decimals) for a token account.
    amount_raw is the integer "amount" from RPC.
    """
    r = cl.get_token_account_balance(Pubkey.from_string(token_acc))
    try:
        v = r.value
        return int(v.amount), int(v.decimals)
    except Exception:
        v = r["result"]["value"]
        return int(v["amount"]), int(v["decimals"])


def list_suspected_nfts(cl: SolClient, owner: Pubkey) -> List[Tuple[str, str]]:
    """
    Heuristic NFT list: token accounts with amount==1 and decimals==0.
    Returns list of (mint, token_account).
    (We’ll add a proper Metaplex metadata fetch and Raydium allowlist later.)
    """
    accounts = _get_all_token_accounts(cl, owner)
    out: List[Tuple[str, str]] = []
    for ta in accounts:
        try:
            amt, dec = _token_balance_decimals(cl, ta)
            if dec == 0 and amt == 1:
                # fetch the mint via getAccountInfo owner snapshot
                ai = cl.get_account_info(Pubkey.from_string(ta))
                # Account data layout: parse via token program; to keep light, use parsed response:
                # Prefer parsedJson if available.
                mint = None
                try:
                    mint = ai.value.data.parsed["info"]["mint"]  # type: ignore[attr-defined]
                except Exception:
                    mint = (ai["result"]["value"]["data"]["parsed"]["info"]["mint"]
                            if ai.get("result") else None)
                if mint:
                    out.append((mint, ta))
        except Exception:
            continue
    return out


def print_nfts(nfts: List[Tuple[str, str]]):
    if not nfts:
        print("   (no NFT-like token accounts found)")
        return
    for mint, ta in nfts:
        mshort = f"{mint[:6]}…{mint[-6:]}"
        tshort = f"{ta[:6]}…{ta[-6:]}"
        print(f"   🖼️  mint {mshort}   • acct {tshort}")


# ---------- Menu ----------

def main():
    rpc = _resolve_rpc_url()
    cl = SolClient(rpc)
    while True:
        banner("🌊 Raydium Core Console", f"RPC: {rpc_cfg.redacted(rpc) if 'helius' in rpc else rpc}")
        print("❯ 1) 🔑  Show loaded wallet")
        print("  2) 🖼️  List NFT-like tokens (amount=1/dec=0)")
        print("  3) 💎  List Raydium NFTs (COMING SOON: allowlist filter)")
        print("  0) 🚪  Exit")
        choice = ask("\nPick", "1")
        if choice == "1":
            owner = show_wallet(cl)
            pause()
        elif choice == "2":
            owner = show_wallet(cl)
            print("\n🕵️  Scanning token accounts for NFT pattern…")
            nftish = list_suspected_nfts(cl, owner)
            print(f"   Found {len(nftish)} candidates\n")
            print_nfts(nftish)
            pause()
        elif choice == "3":
            print("\n💎 Raydium filtered view will use a creator/collection allowlist next pass.")
            print("   (We’ll wire a JSON allowlist and optionally query metadata PDAs.)")
            pause()
        elif choice == "0":
            print("\n👋 Done.")
            return
        else:
            print("   Unknown option.")


if __name__ == "__main__":
    main()
