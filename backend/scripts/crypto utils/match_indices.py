import os, re, sys, argparse
from pathlib import Path

from dotenv import load_dotenv
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes, Bip32Slip10Ed25519
import nacl.signing, base58

def load_env():
    load_dotenv(override=False)
    here = Path(__file__).resolve()
    root_env = here.parents[2] / ".env"
    if root_env.exists():
        load_dotenv(root_env, override=True)

def parse_addrs(s: str) -> list[str]:
    parts = re.split(r"[,\s]+", s.strip())
    return [p for p in parts if p]

def get_targets(args) -> list[str]:
    if args.addresses:
        return parse_addrs(args.addresses)
    env_s = (os.getenv("ADDRESSES") or "").strip()
    if env_s:
        return parse_addrs(env_s)
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip()]
    sys.exit("❌ Provide --addresses, or set ADDRESSES in .env, or pass --file.")

def addr_from_priv32(priv32: bytes) -> str:
    sk = nacl.signing.SigningKey(priv32)
    return base58.b58encode(sk.verify_key.encode()).decode()

def try_bip44(mnemonic: str, account_idx: int, addr_idx: int, change_val: int) -> str:
    """Standard BIP44 (non-hardened change/index)."""
    seed = Bip39SeedGenerator(mnemonic).Generate()
    change_enum = Bip44Changes.CHAIN_EXT if change_val == 0 else Bip44Changes.CHAIN_INT
    ctx = (
        Bip44.FromSeed(seed, Bip44Coins.SOLANA)
        .Purpose().Coin().Account(account_idx)
        .Change(change_enum).AddressIndex(addr_idx)
    )
    return addr_from_priv32(ctx.PrivateKey().Raw().ToBytes())

def try_path(seed: bytes, path: str) -> str:
    """Slip10 ed25519 custom path (lets us test legacy/hardened combos)."""
    node = Bip32Slip10Ed25519.FromSeed(seed)
    node = node.DerivePath(path)
    return addr_from_priv32(node.PrivateKey().Raw().ToBytes())

def main():
    load_env()
    ap = argparse.ArgumentParser(
        description=("Map Solana addresses to mnemonic derivation.\n"
                     "Scans: BIP44(account/addr/change), plus legacy paths: "
                     "m/44'/501'/{acc}', m/44'/501'/{acc}'/0', m/44'/501'/{acc}'/0/{addr}, m/501'/{acc}'/0/{addr}")
    )
    ap.add_argument("--mnemonic", help="12/24 words; if omitted reads MNEMONIC from .env")
    ap.add_argument("--addresses", help="Comma/space/newline-separated addresses; overrides .env ADDRESSES")
    ap.add_argument("--file", help="Text file with one address per line (fallback)")
    ap.add_argument("--max-account", type=int, default=int(os.getenv("MAX_ACCOUNT", "50")))
    ap.add_argument("--max-addr", type=int, default=int(os.getenv("MAX_ADDR", "50")))
    ap.add_argument("--changes", default=os.getenv("CHANGES", "0,1"))
    args = ap.parse_args()

    mnemonic = (args.mnemonic or os.getenv("MNEMONIC") or "").strip().strip('"').strip("'")
    if not mnemonic:
        sys.exit("❌ Provide --mnemonic or set MNEMONIC in .env")
    targets = set(get_targets(args))
    if not targets:
        sys.exit("❌ No target addresses given")

    seed = Bip39SeedGenerator
