from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

from solders.pubkey import Pubkey

IDL_PATH = os.path.join(os.path.dirname(__file__), "idl", "jupiter_perpetuals.json")

from backend.services.solana_rpc import rpc_post as _rpc


def load_idl() -> Dict[str, Any]:
    with open(IDL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def program_id_from_idl(idl: Dict[str, Any]) -> Pubkey:
    addr = idl.get("metadata", {}).get("address") or idl.get("address")
    if not addr:
        raise RuntimeError("Perps IDL missing program address (metadata.address/address)")
    return Pubkey.from_string(addr)


def derive_position_pda(owner: Pubkey, market: str, program_id: Pubkey) -> Pubkey:
    """
    Uses your canonical wrapper if present; otherwise fallback to common seed ["position", owner, market].
    """
    try:
        from backend.perps.pdas import position_pda as _position_pda

        return _position_pda(owner, market, program_id)
    except Exception:
        seed = b"position" + bytes(owner) + market.encode("utf-8")
        return Pubkey.find_program_address([seed], program_id)[0]


def account_exists(pubkey: Pubkey) -> Tuple[bool, int, int]:
    """
    Returns (exists, lamports, dataLen) for the account.
    """
    res = _rpc("getAccountInfo", [str(pubkey), {"encoding": "base64", "commitment": "confirmed"}])
    v = res.get("value")
    if not v:
        return (False, 0, 0)
    data = v.get("data") or ["", ""]
    return (True, int(v.get("lamports") or 0), len((data[0] or b"")))


def probe_position(owner_str: str, market: str) -> Dict[str, Any]:
    idl = load_idl()
    program_id = program_id_from_idl(idl)
    owner = Pubkey.from_string(owner_str)
    pos_pda = derive_position_pda(owner, market, program_id)
    exists, lamports, data_len = account_exists(pos_pda)
    return {
        "programId": str(program_id),
        "owner": owner_str,
        "market": market,
        "positionPda": str(pos_pda),
        "exists": exists,
        "lamports": lamports,
        "dataLen": data_len,
    }


def idl_summary() -> Dict[str, Any]:
    idl = load_idl()
    prog = program_id_from_idl(idl)
    return {
        "programId": str(prog),
        "instructions": len(idl.get("instructions", [])),
        "accounts": len(idl.get("accounts", [])),
    }
