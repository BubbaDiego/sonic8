# backend/services/perps/markets.py
from __future__ import annotations

import base64
import hashlib
from typing import Dict, List

from backend.services.perps.raw_rpc import _rpc, get_program_id, get_idl_account_names


def _disc(name: str) -> bytes:
    # Anchor discriminator = first 8 bytes of sha256(b"account:" + name)
    return hashlib.sha256(f"account:{name}".encode("utf-8")).digest()[:8]


def _data_bytes(acc: dict) -> bytes:
    """
    Accept both Solana and Helius shapes:
      - ["<b64>", "base64"]
      - {"encoded":"<b64>", "encoding":"base64"}
    """
    data = acc.get("account", {}).get("data")
    if isinstance(data, list) and data:
        # ["<b64>", "base64"]
        try:
            return base64.b64decode(data[0])
        except Exception:
            return b""
    if isinstance(data, dict) and "encoded" in data:
        # {"encoded":"<b64>", "encoding":"base64"}
        try:
            return base64.b64decode(data["encoded"])
        except Exception:
            return b""
    return b""


def list_markets_sync() -> Dict[str, object]:
    """
    SAFE FALLBACK: return ONLY pubkeys of Pool and Custody accounts.
    No Anchor decode (avoids IDL mismatch errors).
    """
    program_id = get_program_id()
    idl_accounts = get_idl_account_names()

    pool_name = next((n for n in idl_accounts if n.lower() == "pool"), None)
    custody_name = next((n for n in idl_accounts if n.lower() == "custody"), None)
    if not pool_name or not custody_name:
        # still try with common names even if IDL is missing
        pool_name = pool_name or "Pool"
        custody_name = custody_name or "Custody"

    res = _rpc("getProgramAccounts", [program_id, {"encoding": "base64"}])
    rows = res or []

    disc_pool = _disc(pool_name)
    disc_cust = _disc(custody_name)

    pools: List[dict] = []
    custodies: List[dict] = []

    for it in rows:
        pk = it.get("pubkey")
        raw = _data_bytes(it)
        if len(raw) < 8:
            continue
        head = raw[:8]
        if head == disc_pool:
            pools.append({"pubkey": pk})
        elif head == disc_cust:
            custodies.append({"pubkey": pk})

    return {
        "ok": True,
        "programId": program_id,
        "accounts": idl_accounts,
        "poolsCount": len(pools),
        "custodiesCount": len(custodies),
        "pools": pools,
        "custodies": custodies,
        "note": "pubkey-only fallback; replace IDL with canonical JSON to re-enable decode",
    }
