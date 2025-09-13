# backend/services/perps/positions.py
from __future__ import annotations

import base64
from typing import Dict, List, Optional

from backend.services.perps.raw_rpc import _rpc, get_program_id, get_idl_account_names
from backend.services.perps.config import get_disc, get_account_name


def _filter_params(disc: bytes) -> dict:
    return {
        "encoding": "base64",
        "filters": [
            {"memcmp": {"offset": 0, "bytes": base64.b64encode(disc).decode("utf-8")}}
        ],
        "commitment": "confirmed"
    }


def list_positions_sync(owner: Optional[str]) -> Dict[str, object]:
    """
    SAFE, FAST: return ONLY pubkeys for Position accounts with server-side filter.
    Owner filter is disabled in fallback mode (we’re not decoding yet).
    """
    program_id = get_program_id()
    idl_accounts = get_idl_account_names()

    pos_name_cfg = get_account_name("position", "Position")
    pos_disc = get_disc("position", pos_name_cfg)

    items: List[dict] = []
    try:
        res = _rpc("getProgramAccounts", [program_id, _filter_params(pos_disc)])
        for it in (res or []):
            items.append({"pubkey": it.get("pubkey")})
    except Exception as e:
        return {"ok": False, "error": f"Position GPA failed: {e}"}

    return {
        "ok": True,
        "programId": program_id,
        "accountsFromIDL": idl_accounts,
        "usingAccountNames": {"position": pos_name_cfg},
        "count": len(items),
        "items": items,
        "note": "pubkey-only fallback with configurable discriminator; set PERPS_POSITION_* envs if needed."
    }
