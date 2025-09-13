from __future__ import annotations

from typing import Any, Dict, Optional
from dataclasses import asdict, is_dataclass

from solders.pubkey import Pubkey

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


async def list_positions(owner: Optional[str]) -> Dict[str, Any]:
    """
    Reads Position accounts; filters by owner if provided.
    Returns raw decoded account dicts so we can map fields after we inspect IDL.
    """
    program, client = await get_perps_program()
    try:
        accs = await program.account["Position"].all()
        items = []
        for a in accs:
            aj = _to_jsonish(a.account)
            # Try to detect an 'owner' field to filter; fallback to client-side filter
            pos_owner = None
            if isinstance(aj, dict):
                for k in ("owner", "authority", "user", "trader"):
                    if k in aj:
                        pos_owner = aj[k]
                        break
            include = True
            if owner and pos_owner:
                include = (str(pos_owner) == owner)
            if include:
                items.append({
                    "pubkey": str(a.pubkey),
                    "owner": str(pos_owner) if pos_owner else None,
                    "data": aj
                })
        # NOTE: PnL, borrow fee, funding fee etc will be computed after we solidify field names.
        return {"ok": True, "count": len(items), "items": items}
    finally:
        await client.close()
