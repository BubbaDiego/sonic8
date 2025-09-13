from __future__ import annotations

from typing import Any, Dict

from backend.services.perps.client import get_perps_program
from backend.services.perps.util import (
    fetch_accounts_of_type,
    idl_account_names,
)


async def list_markets() -> Dict[str, Any]:
    """
    Reads Perps 'Pool' and 'Custody' accounts using raw getProgramAccounts +
    Anchor decode (works with Helius or standard RPC).
    """
    program, client = await get_perps_program()
    try:
        names = idl_account_names(program)
        pools, custodies = [], []

        # choose best matching account names (case-insensitive)
        pool_name = next((n for n in names if n.lower() == "pool"), None)
        custody_name = next((n for n in names if n.lower() == "custody"), None)

        if not pool_name or not custody_name:
            return {"ok": False, "error": f"IDL accounts not found. Have: {names}"}

        try:
            rows = await fetch_accounts_of_type(program, pool_name)
            pools = [{"pubkey": pk, "data": row} for pk, row in rows]
        except Exception as e:
            pools = [{"error": f"Pool fetch failed: {type(e).__name__}: {e}"}]

        try:
            rows = await fetch_accounts_of_type(program, custody_name)
            custodies = []
            for pk, row in rows:
                mint = row.get("mint") if isinstance(row, dict) else None
                decimals = row.get("decimals") if isinstance(row, dict) else None
                custodies.append(
                    {
                        "pubkey": pk,
                        "mint": mint,
                        "decimals": decimals,
                        "data": row,
                    }
                )
        except Exception as e:
            custodies = [
                {"error": f"Custody fetch failed: {type(e).__name__}: {e}"}
            ]

        return {
            "ok": True,
            "accounts": names,
            "poolsCount": len(pools),
            "custodiesCount": len(custodies),
            "pools": pools,
            "custodies": custodies,
        }
    finally:
        await client.close()

