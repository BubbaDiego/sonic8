try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import asyncio
import json

from backend.config.rpc import helius_url, redacted
from solana.rpc.async_api import AsyncClient


async def main() -> None:
    url = helius_url()
    print(f"Using Helius RPC  : {redacted(url)}")
    client = AsyncClient(url, commitment="processed")
    resp = await client.get_latest_blockhash()
    await client.close()
    if resp.get("result"):
        print("HTTP 200")
        print(json.dumps(resp, indent=2))
        print("\nHelius RPC OK ✅")
    else:
        print("Helius RPC issue:\n", json.dumps(resp, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
