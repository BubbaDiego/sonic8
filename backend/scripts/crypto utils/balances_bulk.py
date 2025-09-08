import os, sys, asyncio, argparse
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

TOKEN_PROGRAM            = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

MAIN_USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
MAIN_WETH = "7vfCXTkWz5bTj5BTnU9K3ZG3SHrG8Q8Zp8u2f2rLQhQk"
MAIN_WBTC = "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E"

DEV_USDC = os.getenv("DEVNET_MINT_USDC", MAIN_USDC)
DEV_WETH = os.getenv("DEVNET_MINT_WETH", MAIN_WETH)
DEV_WBTC = os.getenv("DEVNET_MINT_WBTC", MAIN_WBTC)

def ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    pda, _ = Pubkey.find_program_address([bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)], ASSOCIATED_TOKEN_PROGRAM)
    return pda

async def ui_bal(c: AsyncClient, owner: Pubkey, mint: Pubkey):
    a = ata(owner, mint)
    info = await c.get_account_info(a)
    if info.value is None:
        return 0.0, a, False
    bal = await c.get_token_account_balance(a)
    try:
        ui = float(bal.value.ui_amount_string or "0")
    except Exception:
        ui = 0.0
    return ui, a, True

async def snapshot_one(c: AsyncClient, owner: Pubkey, mints: Dict[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    lamports = (await c.get_balance(owner)).value
    out["SOL"] = f"{lamports/1_000_000_000:.9f}"
    for label, mint_str in mints.items():
        ui, a, ok = await ui_bal(c, owner, Pubkey.from_string(mint_str))
        out[label] = f"{ui:.6f} (ATA: {str(a)}{' ✅' if ok else ' ❌ not found'})"
    # also print any SPLs with non-zero balance
    r = await c.get_token_accounts_by_owner_json_parsed(owner, {"programId": str(TOKEN_PROGRAM)})
    extras = []
    for it in r.value or []:
        info = it.account.data.parsed["info"]
        ui = float(info["tokenAmount"].get("uiAmountString") or 0)
        if ui > 0:
            extras.append(f"{info['mint']}={ui}")
    if extras:
        out["OTHER>0"] = ", ".join(extras)
    return out

async def both_nets(owner: Pubkey, main_rpc: str, dev_rpc: str):
    main = AsyncClient(main_rpc, commitment=Confirmed)
    dev  = AsyncClient(dev_rpc,  commitment=Confirmed)
    main_mints = {"USDC": MAIN_USDC, "ETH": MAIN_WETH, "BTC": MAIN_WBTC}
    dev_mints  = {"USDC": DEV_USDC,  "ETH": DEV_WETH,  "BTC": DEV_WBTC}
    m_out, d_out = await asyncio.gather(
        snapshot_one(main, owner, main_mints),
        snapshot_one(dev,  owner, dev_mints),
    )
    await asyncio.gather(main.close(), dev.close())
    return m_out, d_out

def read_addresses(args) -> List[str]:
    if args.addresses:
        return [x.strip() for x in args.addresses.split(",") if x.strip()]
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    print("❌ Provide --addresses a,b,c or --file path")
    sys.exit(2)

async def main():
    ap = argparse.ArgumentParser(description="Balances for many addresses on mainnet & devnet")
    ap.add_argument("--addresses", help="Comma-separated list of base58 pubkeys")
    ap.add_argument("--file", help="Text file with one pubkey per line")
    ap.add_argument("--mainnet", default="https://api.mainnet-beta.solana.com")
    ap.add_argument("--devnet",  default="https://api.devnet.solana.com")
    args = ap.parse_args()

    addrs = read_addresses(args)
    for addr in addrs:
        owner = Pubkey.from_string(addr)
        m_out, d_out = await both_nets(owner, args.mainnet, args.devnet)
        print(f"\nAddress: {addr}")
        print("— Mainnet —")
        for k in ("SOL", "USDC", "ETH", "BTC"):
            print(f"{k:<4}: {m_out.get(k,'-')}")
        if "OTHER>0" in m_out:
            print("OTHER>0:", m_out["OTHER>0"])
        print("\n— Devnet —")
        for k in ("SOL", "USDC", "ETH", "BTC"):
            print(f"{k:<4}: {d_out.get(k,'-')}")
        if "OTHER>0" in d_out:
            print("OTHER>0:", d_out["OTHER>0"])

if __name__ == "__main__":
    asyncio.run(main())
