import argparse
import asyncio
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Finalized
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID as TOKEN_PROGRAM

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pubkey", required=True)
    ap.add_argument("--rpc", default="https://api.mainnet-beta.solana.com")
    args = ap.parse_args()

    owner = Pubkey.from_string(args.pubkey)
    c = AsyncClient(args.rpc, commitment=Finalized)
    r = await c.get_token_accounts_by_owner_json_parsed(owner, {"programId": str(TOKEN_PROGRAM)})
    for it in (r.value or []):
        print(it)
    await c.close()

if __name__ == "__main__":
    asyncio.run(main())
