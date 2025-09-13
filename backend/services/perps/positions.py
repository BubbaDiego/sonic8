# backend/services/perps/positions.py
from __future__ import annotations

from typing import Any, Dict, Optional
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
    names = [acc.name for acc in (program.idl.accounts or [])]
    for n in names:
        if n.lower() == target_name.lower():
            return program.account[n]
    raise RuntimeError(f"IDL has no account '{target_name}'. Available: {names}")


async def list_positions(owner: Optional[str]) -> Dict[str, Any]:
    """
    Reads Position accounts; filters by owner if provided.
    Returns raw decoded account dicts so we can map fields after we inspect IDL.
    """
    program, client = await get_perps_program()
    try:
        pos_client = _account_client(program, "Position")
        accs = await pos_client.all()

        items = []
        for a in accs:
            aj = _to_jsonish(a.account)

            # best-effort detection of owner field in IDL struct
            pos_owner = None
            if isinstance(aj, dict):
                for k in ("owner", "authority", "user", "trader"):
                    if k in aj:
                        pos_owner = str(aj[k])
                        break

            include = True
            if owner and pos_owner:
                include = (pos_owner == owner)

            if include:
                items.append({
                    "pubkey": str(a.pubkey),
                    "owner": pos_owner,
                    "data": aj
                })

        return {"ok": True, "count": len(items), "items": items}
    finally:
        await client.close()
