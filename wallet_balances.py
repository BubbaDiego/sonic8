import argparse
import asyncio
from typing import Dict

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Finalized
from solders.pubkey import Pubkey
from spl.token.instructions import get_associated_token_address
from spl.token.constants import TOKEN_PROGRAM_ID as TOKEN_PROGRAM

LAMPORTS_PER_SOL = 1_000_000_000

async def fetch_spl_ui_balance(c: AsyncClient, owner: Pubkey, mint: Pubkey):
    ata = get_associated_token_address(owner, mint)
    try:
        res = await c.get_token_account_balance(ata)
    except Exception:
        return 0.0, ata, False
    if res.value is None:
        return 0.0, ata, False
    ui = res.value.ui_amount_string
    amount = float(ui) if ui is not None else float(res.value.ui_amount or 0)
    return amount, ata, True

async def one_network_snapshot(rpc: str, owner: Pubkey, mints: Dict[str, str], scan_all: bool=False) -> Dict[str, str]:
    c = AsyncClient(rpc, commitment=Finalized)
    out: Dict[str, str] = {}
    bal = await c.get_balance(owner, Finalized)
    out["SOL"] = f"{bal.value / LAMPORTS_PER_SOL:.9f} SOL ({bal.value} lamports)"

    # SPLs (fixed set you already show, e.g., USDC/wETH/BTC...)
    for label, mint_str in mints.items():
        mint = Pubkey.from_string(mint_str)
        ui, a, ok = await fetch_spl_ui_balance(c, owner, mint)
        out[label] = f"{ui:.6f} (ATA: {str(a)}{' ✅' if ok else ' ❌ not found'})"

    # Optionally list any other SPL tokens that have a non-zero balance
    if scan_all:
        r = await c.get_token_accounts_by_owner_json_parsed(owner, {"programId": str(TOKEN_PROGRAM)})
        extras = []
        for it in (r.value or []):
            info = it.account.data.parsed["info"]
            ui = float(info["tokenAmount"].get("uiAmountString") or 0)
            if ui > 0:
                extras.append(f"{info['mint']}={ui}")
        if extras:
            out["OTHER>0"] = ", ".join(extras)

    await c.close()
    return out

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pubkey", required=True, help="Wallet public key")
    ap.add_argument("--mainnet", default="https://api.mainnet-beta.solana.com", help="Mainnet RPC URL")
    ap.add_argument("--devnet", default="https://api.devnet.solana.com", help="Devnet RPC URL")
    ap.add_argument("--all", action="store_true", help="Scan and show any SPL tokens with non-zero balances")
    args = ap.parse_args()

    owner = Pubkey.from_string(args.pubkey)

    main_mints: Dict[str, str] = {
        "USDC": "EPjFWdd5AufqSSqeM2q7Xk6veMZ53EDdivAKov2nYkDr",
        "wETH": "7vfCXTUXEE9f6xMLShx2a1M932aodui6RKpR3zpi27p",
        "wBTC": "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",
    }
    dev_mints: Dict[str, str] = {}

    main_out, dev_out = await asyncio.gather(
        one_network_snapshot(args.mainnet, owner, main_mints, scan_all=args.all),
        one_network_snapshot(args.devnet,  owner, dev_mints,  scan_all=args.all),
    )

    print("Mainnet:")
    for k, v in main_out.items():
        print(f"{k}: {v}")
    print("\nDevnet:")
    for k, v in dev_out.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    asyncio.run(main())
