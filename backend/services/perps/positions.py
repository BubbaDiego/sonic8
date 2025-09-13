# backend/services/perps/positions.py
from __future__ import annotations

import base64
import hashlib
from typing import Dict, List, Optional

from backend.services.perps.raw_rpc import _rpc, get_program_id, get_idl_account_names


def _disc(name: str) -> bytes:
    return hashlib.sha256(f"account:{name}".encode("utf-8")).digest()[:8]


def _data_bytes(acc: dict) -> bytes:
    data = acc.get("account", {}).get("data")
    if isinstance(data, list) and data:
        try:
            return base64.b64decode(data[0])
        except Exception:
            return b""
    if isinstance(data, dict) and "encoded" in data:
        try:
            return base64.b64decode(data["encoded"])
        except Exception:
            return b""
    return b""


def list_positions_sync(owner: Optional[str]) -> Dict[str, object]:
    """
    SAFE FALLBACK: return ONLY pubkeys for Position accounts (no decode).
    Owner filtering is disabled in fallback mode.
    """
    program_id = get_program_id()
    idl_accounts = get_idl_account_names()

    pos_name = next((n for n in idl_accounts if n.lower() == "position"), None) or "Position"

    res = _rpc("getProgramAccounts", [program_id, {"encoding": "base64"}])
    rows = res or []

    disc_pos = _disc(pos_name)
    items: List[dict] = []

    for it in rows:
        pk = it.get("pubkey")
        raw = _data_bytes(it)
        if len(raw) >= 8 and raw[:8] == disc_pos:
            items.append({"pubkey": pk})

    return {
        "ok": True,
        "programId": program_id,
        "count": len(items),
        "items": items,
        "note": "pubkey-only fallback; replace IDL with canonical JSON to re-enable decode",
    }
