# backend/services/perps/markets.py
from __future__ import annotations

from typing import Any, Dict
from dataclasses import asdict, is_dataclass

from backend.services.perps.client import get_perps_program


def _to_jsonish(x: Any) -> Any:
    try:
        if is_dataclass(x):
            return asdict(x)
    except Exception:
        pass
    try:
        return x.__dict__
    except Exception:
        return x


def _account_client(program, target_name: str):
    """
    Return program.account[<name>] by case-insensitive match, with a good error if missing.
    """
    names = [acc.name for acc in (program.idl.accounts or [])]
    for n in names:
        if n.lower() == target_name.lower():
            return program.account[n]
    raise RuntimeError(f"IDL has no account '{target_name}'. Available: {names}")


async def list_markets() -> Dict[str, Any]:
    """
    Reads Perps 'Pool' and 'Custody' accounts and returns a compact markets view.
    """
    program, client = await get_perps_program()
    try:
        pools = []
        custodies = []

        try:
            pool_client = _account_client(program, "Pool")
            acc = await pool_client.all()
            for a in acc:
                pools.append({
                    "pubkey": str(a.pubkey),
                    "data": _to_jsonish(a.account),
                })
        except Exception as e:
            pools = [{"error": f"Pool fetch failed: {type(e).__name__}: {e}"}]

        try:
            custody_client = _account_client(program, "Custody")
            acc = await custody_client.all()
            for a in acc:
                j = _to_jsonish(a.account)
                mint = j.get("mint") if isinstance(j, dict) else None
                decimals = j.get("decimals") if isinstance(j, dict) else None
                custodies.append({
                    "pubkey": str(a.pubkey),
                    "mint": mint,
                    "decimals": decimals,
                    "data": j,
                })
        except Exception as e:
            custodies = [{"error": f"Custody fetch failed: {type(e).__name__}: {e}"}]

        return {
            "ok": True,
            "poolsCount": len(pools) if isinstance(pools, list) else 0,
            "custodiesCount": len(custodies) if isinstance(custodies, list) else 0,
            "pools": pools,
            "custodies": custodies,
        }
    finally:
        await client.close()
