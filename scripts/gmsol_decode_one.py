from __future__ import annotations
import asyncio, base64, json, sys
from typing import Any, Dict, List, Optional

RPC = "https://mainnet.helius-rpc.com/?api-key=a8809bee-20ba-48e9-b841-0bd2bafd60b9"
STORE_PID = "Gmso1uvJnLbawvw7yezdfCDcPydwW2s2iqG3w6MDucLo"
ACCOUNT   = "9TTHBL85q7CpGxkVpgtrSqkXDhyV2TRZjt7vYR3XrhmS"  # ← your match

async def main():
    from solana.rpc.async_api import AsyncClient
    from solana.publickey import PublicKey
    from anchorpy import Idl, Coder

    client = AsyncClient(RPC)
    try:
        # 1) Fetch IDL from chain (if published)
        idl = await Idl.fetch(client, PublicKey(STORE_PID))
        coder = Coder(idl)

        # 2) Get account data (base64)
        resp = await client.get_account_info(PublicKey(ACCOUNT), encoding="base64")
        val = resp.value
        if val is None:
            print("Account not found"); return
        data_b64 = val.data[0] if isinstance(val.data, list) else val.data
        raw = base64.b64decode(data_b64)

        # 3) Try decoding against all IDL accounts
        names: List[str] = [a.name for a in (idl.accounts or [])]
        decoded = None
        account_name = None
        for nm in names:
            try:
                decoded = coder.accounts.decode(nm, raw)
                account_name = nm
                break
            except Exception:
                continue

        if decoded is None:
            print(json.dumps({"decoded": None, "note": "no matching IDL account type"}, indent=2))
            return

        # 4) Convert to dict and print
        d = decoded.__dict__ if hasattr(decoded, "__dict__") else decoded
        print(json.dumps({"account_type": account_name, "data": d}, indent=2, default=str))

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
