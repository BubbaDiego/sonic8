# C:\sonic5\backend\scripts\derive_keypair.py
import os
import sys
import base64
from pathlib import Path
import argparse

from dotenv import load_dotenv
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
import nacl.signing
import base58

def load_env_anywhere() -> None:
    """
    Load .env reliably:
      1) current working dir
      2) project root inferred from this file: <...>\sonic5\.env
      3) script dir and its parents
    """
    # 1) default (CWD)
    load_dotenv(override=False)

    if os.getenv("MNEMONIC"):
        return

    # 2) project root two levels up from this script: ...\backend\scripts -> ...\sonic5
    root_env = Path(__file__).resolve().parents[2] / ".env"
    if root_env.exists():
        load_dotenv(dotenv_path=root_env, override=True)
        if os.getenv("MNEMONIC"):
            return

    # 3) walk up parents in case layout differs
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        env_path = p / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)
            if os.getenv("MNEMONIC"):
                return

def clean_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1].strip()
    return s

def resolve_mnemonic() -> str:
    parser = argparse.ArgumentParser(description="Derive Solana keypair from mnemonic")
    parser.add_argument("--mnemonic", type=str, help="12/24-word seed phrase (quote it)")
    args = parser.parse_args()

    # Priority: CLI > ENV
    if args.mnemonic:
        return clean_quotes(args.mnemonic)

    load_env_anywhere()
    mn = os.getenv("MNEMONIC", "")
    mn = clean_quotes(mn)

    if not mn:
        sys.exit("❌ No mnemonic found. Provide via --mnemonic \"...\" or put MNEMONIC=... in your .env")

    words = mn.split()
    if len(words) not in (12, 24):
        sys.exit(f"❌ Expected 12 or 24 words, got {len(words)}.")
    return mn

def main():
    MNEMONIC = resolve_mnemonic()

    # 1) Seed from mnemonic
    seed_bytes = Bip39SeedGenerator(MNEMONIC).Generate()

    # 2) Derive Solana path m/44'/501'/0'/0'
    bip44_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA)
    acct = bip44_ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)

    priv_key_bytes = acct.PrivateKey().Raw().ToBytes()

    # 3) Ed25519 keypair
    signing_key = nacl.signing.SigningKey(priv_key_bytes)
    verify_key = signing_key.verify_key

    # 4) Encoded outputs
    public_key_b58 = base58.b58encode(verify_key.encode()).decode()
    secret_key_base64 = base64.b64encode(signing_key.encode() + verify_key.encode()).decode()

    print("✅ Public Key (Solana address):", public_key_b58)
    print("✅ Secret Key (base64):", secret_key_base64)
    print("\n👉 Put this in your .env:\nWALLET_SECRET_BASE64=" + secret_key_base64)

if __name__ == "__main__":
    main()
