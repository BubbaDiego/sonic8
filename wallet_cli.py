import os
import argparse
import asyncio
import base64
import json
from solders.keypair import Keypair

parser = argparse.ArgumentParser(description="Wallet helper")
parser.add_argument("--secret-b64", help="Override WALLET_SECRET_BASE64 (base64 of 32-byte seed, 64-byte secret key, or JSON keypair text)")
parser.add_argument("--secret-b64-file", help="Path to a file containing the base64 secret")
parser.add_argument("--expected-pubkey", help="Abort if derived pubkey does not match this address")


def keypair_from_b64(b64: str) -> Keypair:
    raw = base64.b64decode(b64)
    if len(raw) == 32:
        return Keypair.from_seed(raw)
    if len(raw) == 64:
        return Keypair.from_bytes(raw)
    # otherwise treat as json text
    try:
        arr = json.loads(raw.decode("utf-8"))
        if isinstance(arr, list):
            return Keypair.from_bytes(bytes(arr))
    except Exception:
        pass
    raise ValueError("Unknown keypair format")


async def _amain():
    # pick secret source: CLI > file > env
    if args.secret_b64:
        secret_b64 = args.secret_b64.strip()
    elif args.secret_b64_file:
        with open(args.secret_b64_file, "r", encoding="utf-8") as fh:
            secret_b64 = fh.read().strip()
    else:
        secret_b64 = os.getenv("WALLET_SECRET_BASE64") or os.getenv("MNEMONIC_BASE64")
    if not secret_b64:
        raise SystemExit("❌ Missing secret: pass --secret-b64/--secret-b64-file or set WALLET_SECRET_BASE64")

    kp = keypair_from_b64(secret_b64)
    pub = str(kp.pubkey())
    print(f"Wallet: {pub}")
    if args.expected_pubkey and args.expected_pubkey.strip() != pub:
        raise SystemExit(
            f"❌ Secret does not match expected pubkey.\n  expected: {args.expected_pubkey}\n  derived : {pub}")

    # ... continue: fetch balances, fee check, open perps ...


if __name__ == "__main__":
    args = parser.parse_args()
    asyncio.run(_amain())
else:
    args = parser.parse_args([])
