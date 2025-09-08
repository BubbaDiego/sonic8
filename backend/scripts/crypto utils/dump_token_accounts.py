import argparse
import asyncio
import os
from typing import Tuple

from dotenv import load_dotenv
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

# ── Mainnet RPC (override with RPC_URL in .env or --rpc) ───────────────────────
MAINNET_RPC = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")

# ── Program IDs ────────────────────────────────────────────────────────────────
TOKEN_PROGRAM            = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

# ── Canonical mainnet mints (override in .env if your wallet uses different wrappers) ─
USDC_MINT = Pubkey.from_string(os.getenv("MINT_USDC", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"))
WETH_MINT = Pubkey.from_string(os.getenv("MINT_WETH", "7vfCXTkWz5bTj5BTnU9K3ZG3SHrG8Q8Zp8u2f2rLQhQk"))  # Ether (Portal)
WBTC_MINT = Pubkey.from_string(os.getenv("MINT_WBTC", "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E"))  # renBTC-era

# ── Icons (max vibes) ─────────────────────────────────────────────────────────
IC_HDR = "✨"
IC_RPC = "🌐"
IC_ACC = "🔗"
IC_SOL = "◎"
IC_USD = "💵"
IC_ETH = "🟣"
IC_BTC = "🟠"
IC_OK  = "✅"
IC_X   = "❌"

def short(s: str, left=6, right=6) -> str:
    return s if len(s) <= left + right else f"{s[:left]}…{s[-right:]}"

def derive_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    pda, _ = Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)],
        ASSOCIATED_TOKEN_PROGRAM
    )
    return pda

async def spl_ui_balance(client: AsyncClient, owner: Pubkey, mint: Pubkey) -> Tuple[float, Pubkey, bool]:
    ata = derive_ata(owner, mint)
    info = await client.get_account_info(ata)
    if info.value is None:
        return 0.0, ata, False
    bal = await client.get_token_account_balance(ata)
    try:
        ui = float(bal.value.ui_amount_string or "0")
    except Exception:
        ui = 0.0
    return ui, ata, True

def prompt_pubkey() -> Pubkey:
    while True:
        raw = input(f"{IC_ACC}  Address (base58): ").strip()
        try:
            return Pubkey.from_string(raw)
        except Exception:
            print(f"  {IC_X} invalid address, try again.")

def parse_args():
    load_dotenv(override=True)
    ap = argparse.ArgumentParser(
        description="Compact Solana (mainnet) balances: SOL + USDC + WETH + WBTC with ATA status."
    )
    ap.add_argument("--pubkey", help="Owner address (base58). If omitted, you’ll be prompted.")
    ap.add_argument("--rpc", default=MAINNET_RPC, help="RPC URL (default: mainnet-beta).")
    ap.add_argument("--full", action="store_true", help="Show full mint/ATA addresses (no shortening).")
    return ap.parse_args()

async def main():
    args = parse_args()
    owner = Pubkey.from_string(args.pubkey) if args.pubkey else prompt_pubkey()
    rpc   = args.rpc

    c = AsyncClient(rpc, commitment=Confirmed)

    # Header
    print(f"\n{IC_HDR}  Solana wallet snapshot (mainnet)")
    print(f"{IC_ACC}  owner: {owner}")
    print(f"{IC_RPC}  rpc  : {rpc}")

    # SOL
    lamports = (await c.get_balance(owner)).value
    sol = lamports / 1_000_000_000
    print(f"{IC_SOL}  SOL   | bal {sol:.9f}")

    # USDC
    usdc_ui, usdc_ata, usdc_ok = await spl_ui_balance(c, owner, USDC_MINT)
    print(f"{IC_USD}  USDC  | bal {usdc_ui:.6f}  | mint {short(str(USDC_MINT)) if not args.full else USDC_MINT}"
          f"  | ATA {short(str(usdc_ata)) if not args.full else usdc_ata}  {IC_OK if usdc_ok else IC_X}")

    # WETH
    weth_ui, weth_ata, weth_ok = await spl_ui_balance(c, owner, WETH_MINT)
    print(f"{IC_ETH}  WETH  | bal {weth_ui:.6f}  | mint {short(str(WETH_MINT)) if not args.full else WETH_MINT}"
          f"  | ATA {short(str(weth_ata)) if not args.full else weth_ata}  {IC_OK if weth_ok else IC_X}")

    # WBTC
    wbtc_ui, wbtc_ata, wbtc_ok = await spl_ui_balance(c, owner, WBTC_MINT)
    print(f"{IC_BTC}  WBTC  | bal {wbtc_ui:.6f}  | mint {short(str(WBTC_MINT)) if not args.full else WBTC_MINT}"
          f"  | ATA {short(str(wbtc_ata)) if not args.full else wbtc_ata}  {IC_OK if wbtc_ok else IC_X}")

    await c.close()
    print("")  # neat tail

if __name__ == "__main__":
    asyncio.run(main())
