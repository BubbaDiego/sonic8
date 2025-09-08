import os, argparse, asyncio, base64
from pathlib import Path
from typing import Tuple, Dict

from dotenv import load_dotenv
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed

# Optional mnemonic path
try:
    from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
    import nacl.signing, base58
    HAVE_MNEMONIC = True
except Exception:
    HAVE_MNEMONIC = False

TOKEN_PROGRAM            = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

# ---- Mainnet canonical mints ----
MAIN_USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
MAIN_WETH = "7vfCXTkWz5bTj5BTnU9K3ZG3SHrG8Q8Zp8u2f2rLQhQk"  # Wormhole wETH
MAIN_WBTC = "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E"  # legacy renBTC ticker "BTC"

# ---- Devnet mints (override in .env if you have them) ----
DEV_USDC = os.getenv("DEVNET_MINT_USDC", MAIN_USDC)  # you can set devnet mint here
DEV_WETH = os.getenv("DEVNET_MINT_WETH", MAIN_WETH)
DEV_WBTC = os.getenv("DEVNET_MINT_WBTC", MAIN_WBTC)

def load_env():
    # load from CWD and project root
    load_dotenv(override=False)
    here = Path(__file__).resolve()
    root_env = here.parents[2] / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=True)

def ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    pda, _ = Pubkey.find_program_address(
        [bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)],
        ASSOCIATED_TOKEN_PROGRAM
    )
    return pda

def derive_from_env() -> Pubkey | None:
    """Try WALLET_SECRET_BASE64 first; fallback to MNEMONIC (+ MNEMONIC_INDEX)."""
    sk_b64 = os.getenv("WALLET_SECRET_BASE64")
    if sk_b64:
        try:
            kp = Keypair.from_bytes(base64.b64decode(sk_b64))
            return kp.pubkey()
        except Exception:
            pass
    mn = (os.getenv("MNEMONIC") or "").strip().strip('"').strip("'")
    if mn and HAVE_MNEMONIC:
        idx = int(os.getenv("MNEMONIC_INDEX", "0"))
        seed = Bip39SeedGenerator(mn).Generate()
        ctx = Bip44.FromSeed(seed, Bip44Coins.SOLANA).Purpose().Coin().Account(idx).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
        sk = nacl.signing.SigningKey(ctx.PrivateKey().Raw().ToBytes())
        return Pubkey.from_string(base58.b58encode(sk.verify_key.encode()).decode())
    return None

async def fetch_spl_ui_balance(client: AsyncClient, owner: Pubkey, mint: Pubkey) -> Tuple[float, Pubkey, bool]:
    """Return (ui_amount, ata_pubkey, exists)."""
    a = ata(owner, mint)
    info = await client.get_account_info(a)
    if info.value is None:
        return 0.0, a, False
    bal = await client.get_token_account_balance(a)
    try:
        ui = float(bal.value.ui_amount_string or "0")
    except Exception:
        ui = 0.0
    return ui, a, True

async def one_network_snapshot(rpc: str, owner: Pubkey, mints: Dict[str, str]) -> Dict[str, str]:
    c = AsyncClient(rpc, commitment=Confirmed)
    out: Dict[str, str] = {}

    # SOL
    lamports = (await c.get_balance(owner)).value
    sol = lamports / 1_000_000_000
    out["SOL"] = f"{sol:.9f}"

    # SPLs
    for label, mint_str in mints.items():
        mint = Pubkey.from_string(mint_str)
        ui, a, ok = await fetch_spl_ui_balance(c, owner, mint)
        out[label] = f"{ui:.6f} (ATA: {str(a)}{' ✅' if ok else ' ❌ not found'})"

    await c.close()
    return out

async def main():
    load_env()
    ap = argparse.ArgumentParser(description="Print SOL/USDC/wETH/BTC balances on both mainnet & devnet")
    ap.add_argument("--pubkey", help="Solana address (base58). If omitted, uses WALLET_SECRET_BASE64 or MNEMONIC from .env")
    ap.add_argument("--mainnet", default="https://api.mainnet-beta.solana.com", help="Mainnet RPC URL")
    ap.add_argument("--devnet", default="https://api.devnet.solana.com", help="Devnet RPC URL")
    args = ap.parse_args()

    if not args.pubkey:
        owner = derive_from_env()
        if owner is None:
            ap.error("Provide --pubkey or set WALLET_SECRET_BASE64 (or MNEMONIC) in .env")
    else:
        owner = Pubkey.from_string(args.pubkey)

    print(f"Address: {str(owner)}", flush=True)

    main_mints = {
        "USDC": os.getenv("MINT_USDC", MAIN_USDC),
        "ETH" : os.getenv("MINT_WETH", MAIN_WETH),
        "BTC" : os.getenv("MINT_WBTC", MAIN_WBTC),
    }
    dev_mints = {
        "USDC": DEV_USDC,
        "ETH" : DEV_WETH,
        "BTC" : DEV_WBTC,
    }

    # Gather both in parallel
    main_out, dev_out = await asyncio.gather(
        one_network_snapshot(args.mainnet, owner, main_mints),
        one_network_snapshot(args.devnet,  owner, dev_mints),
    )

    # Pretty print
    print("\n— Mainnet —", flush=True)
    for k in ("SOL", "USDC", "ETH", "BTC"):
        print(f"{k:<4}: {main_out[k]}", flush=True)

    print("\n— Devnet —", flush=True)
    for k in ("SOL", "USDC", "ETH", "BTC"):
        print(f"{k:<4}: {dev_out[k]}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
