from __future__ import annotations

from typing import Any, Dict, Optional

from backend.services.perps.client import get_perps_program
from backend.services.perps.util import (
    fetch_accounts_of_type,
    idl_account_names,
)


async def list_positions(owner: Optional[str]) -> Dict[str, Any]:
    """
    Reads 'Position' accounts via raw program accounts and Anchor decode.
    Filters by owner if we can identify the owner field (best-effort).
    """
    program, client = await get_perps_program()
    try:
        names = idl_account_names(program)
        pos_name = next((n for n in names if n.lower() == "position"), None)
        if not pos_name:
            return {
                "ok": False,
                "error": f"IDL has no Position account. Accounts: {names}",
            }

        rows = await fetch_accounts_of_type(program, pos_name)
        items = []
        for pk, row in rows:
            pos_owner = None
            if isinstance(row, dict):
                for k in ("owner", "authority", "user", "trader"):
                    if k in row:
                        pos_owner = str(row[k])
                        break
            include = True
            if owner and pos_owner:
                include = pos_owner == owner
            if include:
                items.append({"pubkey": pk, "owner": pos_owner, "data": row})

        return {"ok": True, "count": len(items), "items": items}
    finally:
        await client.close()

