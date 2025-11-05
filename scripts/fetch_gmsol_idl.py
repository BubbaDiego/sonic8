import asyncio, json
from pathlib import Path

# Anchor + Solana (for your pinned versions)
from anchorpy import Idl
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey  # ← correct for solana==0.32 / anchorpy==0.19.1

RPC = "https://mainnet.helius-rpc.com/?api-key=a8809bee-20ba-48e9-b841-0bd2bafd60b9"
PROGRAM_ID = Pubkey.from_string("Gmso1uvJnLbawvw7yezdfCDcPydwW2s2iqG3w6MDucLo")

OUT = Path(r"C:\sonic7\backend\core\gmx_solana_core\idl\gmsol-store.json")

async def main():
    client = AsyncClient(RPC)
    try:
        idl = await Idl.fetch(client, PROGRAM_ID)
        if idl is None:
            raise SystemExit("IDL not published on-chain or fetch failed.")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(idl, indent=2), encoding="utf-8")
        print("✅ Saved:", OUT)
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
