from __future__ import annotations

from typing import Any, Dict
from dataclasses import asdict, is_dataclass

from backend.services.perps.client import get_perps_program


def _to_jsonish(x: Any) -> Any:
    # AnchorPy returns dataclass-like objects; make them JSON friendly.
    try:
        if is_dataclass(x):
            return asdict(x)
    except Exception:
        pass
    try:
        return x.__dict__
    except Exception:
        return x


async def list_markets() -> Dict[str, Any]:
    """
    Reads Perps 'Pool' and 'Custody' accounts and returns a compact markets view.
    NOTE: Field names depend on the exact IDL. We keep it defensive:
    - We attempt program.account["Pool"].all() & program.account["Custody"].all()
    - We emit a minimal set of attributes (+ raw address) so the UI has something now.
    """
    program, client = await get_perps_program()
    try:
        pools = []
        try:
            acc = await program.account["Pool"].all()
            for a in acc:
                pools.append({
                    "pubkey": str(a.pubkey),
                    "data": _to_jsonish(a.account),
                })
        except Exception as e:
            pools = [{"error": f"Pool fetch failed: {type(e).__name__}: {e}"}]

        custodies = []
        try:
            acc = await program.account["Custody"].all()
            for a in acc:
                j = _to_jsonish(a.account)
                # Try to surface a token mint and decimals if present
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

        # Minimal market summary. You can enrich later (funding, OI, fee previews)
        return {
            "ok": True,
            "poolsCount": len(pools) if isinstance(pools, list) else 0,
            "custodiesCount": len(custodies) if isinstance(custodies, list) else 0,
            "pools": pools,
            "custodies": custodies,
        }
    finally:
        await client.close()
