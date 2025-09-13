# backend/services/perps/util.py
from __future__ import annotations

import base64
import hashlib
from typing import Any, Dict, List, Tuple

from solders.pubkey import Pubkey
from anchorpy import Program


def _decode_data_anyshape(acc: Dict[str, Any]) -> bytes | None:
    """
    Support both Solana and Helius data shapes:
    - ["<b64>", "base64"]
    - {"encoded":"<b64>", "encoding":"base64"}
    """
    data = acc.get("account", {}).get("data")
    if isinstance(data, list) and len(data) >= 1:
        try:
            return base64.b64decode(data[0])
        except Exception:
            return None
    if isinstance(data, dict) and "encoded" in data:
        try:
            return base64.b64decode(data["encoded"])
        except Exception:
            return None
    return None


def _account_discriminator(name: str) -> bytes:
    """
    Anchor discriminator = first 8 bytes of sha256(b"account:" + name).
    """
    return hashlib.sha256(f"account:{name}".encode("utf-8")).digest()[:8]


async def fetch_accounts_of_type(
    program: Program, account_name: str, limit: int | None = None
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Use getProgramAccounts with encoding='base64', filter by Anchor discriminator,
    and decode via program.coder.accounts.decode(account_name, raw).
    Works on Helius and standard RPC.
    Returns list of (pubkey, decoded_dict).
    """
    client = program.provider.connection
    resp = await client.get_program_accounts(program.program_id, encoding="base64")
    result = getattr(resp, "value", None) or resp.get("result", [])
    disc = _account_discriminator(account_name)

    out: List[Tuple[str, Dict[str, Any]]] = []
    for it in result:
        pk = it.get("pubkey")
        raw = _decode_data_anyshape(it)
        if not (pk and raw and len(raw) >= 8):
            continue
        if raw[:8] != disc:
            continue  # not this account type
        try:
            decoded = program.coder.accounts.decode(account_name, raw)
            dd = decoded.__dict__ if hasattr(decoded, "__dict__") else decoded
            out.append((pk, dd))
            if limit and len(out) >= limit:
                break
        except Exception:
            continue
    return out


def idl_account_names(program: Program) -> List[str]:
    """Return account names listed in the IDL (case-preserving)."""
    return [acc.name for acc in (program.idl.accounts or [])]
