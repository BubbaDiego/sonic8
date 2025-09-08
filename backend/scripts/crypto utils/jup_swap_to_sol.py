import os, json, base64, asyncio
import httpx
from argparse import ArgumentParser, Namespace
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import to_bytes_versioned
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts

# Optional mnemonic derivation
try:
    from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
    import nacl.signing, base58
    HAVE_MNEMONIC = True
except Exception:
    HAVE_MNEMONIC = False

# Icons
IC_OK="✅"; IC_X="❌"; IC_WAL="👛"; IC_RPC="🌐"; IC_SWAP="🔄"; IC_USD="💵"; IC_SOL="◎"; IC_LOG="🧾"; IC_TX="🔎"

# Constants (overridable via .env)
USDC_MINT = os.getenv("MINT_USDC", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
SOL_MINT  = "So11111111111111111111111111111111111111112"  # wSOL (unwraps to SOL)
RPC_URL   = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")

# Jupiter LITE endpoints
QUOTE_URL = "https://lite-api.jup.ag/swap/v1/quote"
SWAP_URL  = "https://lite-api.jup.ag/swap/v1/swap"

def load_env():
    load_dotenv(override=True)

def ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    TOKEN_PROGRAM            = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    ASSOCIATED_TOKEN_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
    pda, _ = Pubkey.find_program_address([bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)], ASSOCIATED_TOKEN_PROGRAM)
    return pda

def derive_kp_from_mnemonic_index(mnemonic: str, index: int) -> Keypair:
    if not HAVE_MNEMONIC:
        raise SystemExit("pip install bip-utils pynacl (needed for MNEMONIC derivation)")
    seed = Bip39SeedGenerator(mnemonic).Generate()
    ctx = (Bip44.FromSeed(seed, Bip44Coins.SOLANA)
           .Purpose().Coin().Account(index).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0))
    priv = ctx.PrivateKey().Raw().ToBytes()
    sk   = nacl.signing.SigningKey(priv); vk = sk.verify_key
    sec64 = base64.b64encode(sk.encode() + vk.encode()).decode()
    return Keypair.from_bytes(base64.b64decode(sec64))

def resolve_wallet(index_override: int|None):
    load_env()
    # Priority: explicit secret → mnemonic+index override → env mnemonic+index
    secret_b64 = (os.getenv("WALLET_SECRET_BASE64") or "").strip()
    if secret_b64 and index_override is None:
        try:  return Keypair.from_bytes(base64.b64decode(secret_b64))
        except Exception: raise SystemExit("❌ WALLET_SECRET_BASE64 is not valid base64 bytes")
    mnemonic = (os.getenv("MNEMONIC") or "").strip().strip('"').strip("'")
    idx = index_override if index_override is not None else (int(os.getenv("MNEMONIC_INDEX")) if os.getenv("MNEMONIC_INDEX") else None)
    if mnemonic and idx is not None:
        return derive_kp_from_mnemonic_index(mnemonic, idx)
    if secret_b64:  # if we had a secret but index_override was provided without mnemonic
        return Keypair.from_bytes(base64.b64decode(secret_b64))
    raise SystemExit("❌ Provide WALLET_SECRET_BASE64 or MNEMONIC + MNEMONIC_INDEX (or pass --index with MNEMONIC in .env)")

async def spl_ui_balance(client: AsyncClient, owner: Pubkey, mint_str: str) -> float:
    a = ata(owner, Pubkey.from_string(mint_str))
    info = await client.get_account_info(a)
    if info.value is None: return 0.0
    bal = await client.get_token_account_balance(a)
    try: return float(bal.value.ui_amount_string or "0")
    except Exception: return 0.0

def parse_args() -> Namespace:
    load_env()
    ap = ArgumentParser(description="Jupiter swap CLI (usdc<->sol) using lite-api.jup.ag")
    ap.add_argument("--pair", choices=["usdc->sol", "sol->usdc"], help="Swap direction")
    ap.add_argument("--amount", type=float, help="Human units (USDC in USDC, SOL in SOL)")
    ap.add_argument("--slippage-bps", type=int, default=int(os.getenv("SWAP_SLIPPAGE_BPS", "50")), help="Slippage in bps (default 50=0.50%)")
    ap.add_argument("--rpc", default=RPC_URL, help="RPC URL")
    ap.add_argument("--index", type=int, help="Override MNEMONIC_INDEX for MNEMONIC-based signing")
    ap.add_argument("--dry-run", action="store_true", help="Quote only; do not build/send")
    args = ap.parse_args()

    # Interactive fallback if flags omitted
    if not args.pair:
        choice = (input("Swap pair [1=USDC→SOL, 2=SOL→USDC] (default 1): ").strip() or "1")
        args.pair = "usdc->sol" if choice != "2" else "sol->usdc"
    if args.amount is None:
        raw = input(f"Amount ({'USDC' if args.pair=='usdc->sol' else 'SOL'}): ").strip()
        try:
            args.amount = float(raw)
        except Exception:
            raise SystemExit("❌ Invalid amount.")
    return args

async def main():
    args = parse_args()
    kp = resolve_wallet(args.index)
    owner = kp.pubkey()

    print(f"{IC_WAL} Wallet: {owner}")
    print(f"{IC_RPC} RPC   : {args.rpc}")
    print(f"{IC_SWAP} Pair  : {args.pair}  | amount {args.amount} | slip {args.slippage_bps/100:.2f}%")

    # Input/output + amount atoms
    if args.pair == "usdc->sol":
        input_mint, output_mint = USDC_MINT, SOL_MINT
        amount_atoms = int(round(args.amount * 1_000_000))         # USDC atoms (6dp)
    else:
        input_mint, output_mint = SOL_MINT, USDC_MINT
        amount_atoms = int(round(args.amount * 1_000_000_000))     # SOL lamports (9dp)

    client = AsyncClient(args.rpc, commitment=Confirmed)

    # Preflight balances
    lamports = (await client.get_balance(owner)).value
    sol_ui = lamports / 1e9
    usdc_ui = await spl_ui_balance(client, owner, USDC_MINT)
    print(f"{IC_SOL} SOL  : {sol_ui:.9f}   {IC_USD} USDC : {usdc_ui:.6f}")

    # Basic checks
    if args.pair == "usdc->sol":
        need = amount_atoms / 1_000_000
        if usdc_ui + 1e-9 < need:
            await client.close()
            raise SystemExit(f"{IC_X} Not enough USDC to swap {need:.6f}.")
    else:
        # keep a small reserve to avoid bricking the account (fee/rent)
        reserve_sol = float(os.getenv("SOL_RESERVE", "0.002"))
        max_spendable = max(0.0, sol_ui - reserve_sol)
        if args.amount > max_spendable + 1e-12:
            await client.close()
            raise SystemExit(f"{IC_X} Insufficient SOL. Max spendable ≈ {max_spendable:.6f} (keeping {reserve_sol} SOL reserve).")

    # 1) Quote
    params = {
        "inputMint":  input_mint,
        "outputMint": output_mint,
        "amount":     str(amount_atoms),
        "slippageBps": str(args.slippage_bps),
        "preferDirectRoutes": "true",
        "onlyDirectRoutes": "false",
    }

    async with httpx.AsyncClient(timeout=30) as http:
        q = await http.get(QUOTE_URL, params=params)
        if q.status_code != 200:
            print(f"{IC_X} Quote HTTP error:", q.status_code, q.text); await client.close(); return
        quote = q.json()
        if args.dry_run:
            print(f"{IC_LOG} Quote:", json.dumps(quote, indent=2))
            await client.close(); return

        # 2) Build swap tx
        body = {
            "quoteResponse": quote,
            "userPublicKey": str(owner),
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "dynamicSlippage": True
        }
        t = await http.post(SWAP_URL, headers={"content-type": "application/json"}, data=json.dumps(body))
        try:
            tx_resp = t.json()
        except Exception:
            print(f"{IC_X} Build error (non-JSON):", t.text); await client.close(); return
        if t.status_code != 200 or "swapTransaction" not in tx_resp:
            print(f"{IC_X} Jupiter build error payload:")
            print(json.dumps(tx_resp, indent=2)); await client.close(); return

    # 3) Sign & send
    raw  = base64.b64decode(tx_resp["swapTransaction"])
    vtx  = VersionedTransaction.from_bytes(raw)
    sig  = kp.sign_message(to_bytes_versioned(vtx.message))
    sent = VersionedTransaction.populate(vtx.message, [sig])

    try:
        res = await client.send_raw_transaction(bytes(sent), opts=TxOpts(skip_preflight=False, max_retries=5))
        txid = res.value
        print(f"{IC_OK} Sent: {txid}")
        print(f"{IC_TX} Solscan: https://solscan.io/tx/{txid}")
    finally:
        await client.close()

if __name__ == "__main__":2
    asyncio.run(main())
