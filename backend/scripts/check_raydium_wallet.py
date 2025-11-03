from __future__ import annotations

import argparse
import json
import os

from backend.core.raydium_core.raydium_core import RaydiumCore


def main():
    p = argparse.ArgumentParser(description="Headless wallet balance check via Solana RPC")
    p.add_argument("--owner", help="Wallet pubkey (base58). If omitted, uses WALLET_SECRET_BASE64 via WalletCore.", default=None)
    p.add_argument("--include-zero", action="store_true")
    p.add_argument("--no-enrich", action="store_true", help="Skip Raydium token list enrichment.")
    args = p.parse_args()

    core = RaydiumCore(rpc_url=os.getenv("RPC_URL"), raydium_api_base=os.getenv("RAYDIUM_API_BASE"))
    owner = args.owner
    if not owner:
        from backend.core.wallet_core.wallet_core import WalletCore  # lazy import

        owner = WalletCore().get_default_public_key_base58()

    out = core.get_wallet_balances(owner, include_zero=args.include_zero, enrich_meta=not args.no_enrich)
    print(json.dumps(out.model_dump(), indent=2))


if __name__ == "__main__":
    main()
