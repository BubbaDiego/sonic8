import argparse
import asyncio
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Finalized
from solders.pubkey import Pubkey

LAMPORTS_PER_SOL = 1_000_000_000

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--addresses", required=True, help="Comma-separated list of addresses")
    ap.add_argument("--mainnet", default="https://api.mainnet-beta.solana.com")
    ap.add_argument("--devnet", default="https://api.devnet.solana.com")
    args = ap.parse_args()

    addresses = [a.strip() for a in args.addresses.split(",") if a.strip()]

    main = AsyncClient(args.mainnet, commitment=Finalized)
    dev = AsyncClient(args.devnet, commitment=Finalized)

    for addr in addresses:
        pk = Pubkey.from_string(addr)
        bal_main = await main.get_balance(pk, Finalized)
        bal_dev = await dev.get_balance(pk, Finalized)
        print(f"{addr}: mainnet {bal_main.value / LAMPORTS_PER_SOL:.9f} SOL | devnet {bal_dev.value / LAMPORTS_PER_SOL:.9f} SOL")

    await main.close()
    await dev.close()

if __name__ == "__main__":
    asyncio.run(main())
