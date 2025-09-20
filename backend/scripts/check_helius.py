# Loads .env and does a single JSON-RPC call (blockhash) via the same client setup
import asyncio
try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(), override=True)
except Exception:
    pass

from backend.infra.solana_client import get_async_client


async def main():
    client = get_async_client()
    resp = await client.get_latest_blockhash()
    await client.close()
    ok = bool(resp.get("result"))
    print("HTTP 200" if ok else "HTTP ?")
    print(resp)
    print("\nHelius RPC OK ✅" if ok else "\nHelius RPC problem ❌")


if __name__ == "__main__":
    asyncio.run(main())
