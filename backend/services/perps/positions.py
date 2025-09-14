# backend/services/perps/positions.py
from __future__ import annotations

import os
from typing import Dict, List, Optional

from backend.services.perps.raw_rpc import _rpc, get_program_id, get_idl_account_names
from backend.services.perps.config import get_disc, get_account_name  # env-driven names/discriminators

# ---- tiny base58 encoder (no extra deps) ----
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def _b58enc(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = _B58[0] if n == 0 else ""
    out = []
    while n:
        n, r = divmod(n, 58)
        out.append(_B58[r])
    s += "".join(reversed(out))
    # preserve leading zeros
    z = 0
    for ch in b:
        if ch == 0: z += 1
        else: break
    return (_B58[0] * z) + s


def _params_b58(disc_b58: str, owner_b58: Optional[str], owner_off: Optional[int]) -> dict:
    flt = [{"memcmp": {"offset": 0, "bytes": disc_b58}}]
    if owner_b58 and owner_off is not None:
        flt.append({"memcmp": {"offset": int(owner_off), "bytes": owner_b58}})
    return {"encoding": "base64", "commitment": "confirmed", "filters": flt}


def _env_owner_off() -> Optional[int]:
    v = (os.getenv("PERPS_POSITION_OWNER_OFFSET") or "").strip()
    if not v: return None
    try: return int(v)
    except Exception: return None


def _quick_offsets() -> List[int]:
    # Common owner offsets after the 8-byte discriminator; cheap to try
    base = 8
    return [base + x for x in (0, 32, 40, 48, 64, 72, 80, 96, 104, 112, 128, 136, 144)]


def list_positions_sync(owner: Optional[str]) -> Dict[str, object]:
    """
    Return pubkeys for Position accounts, filtered by owner if possible.
    Priority for the owner offset:
      1) PERPS_POSITION_OWNER_OFFSET (env)
      2) quick guess list (stop at first nonzero)
      3) fallback: all positions (discriminator only)
    """
    program_id = get_program_id()
    idl_accounts = get_idl_account_names()

    pos_name = get_account_name("position", "Position")
    disc_b58 = _b58enc(get_disc("position", pos_name))
    owner_b58 = (owner or "").strip() or None

    # no owner → show all positions (pubkeys only)
    if not owner_b58:
        items: List[dict] = []
        res = _rpc("getProgramAccounts", [program_id, _params_b58(disc_b58, None, None)])
        for it in (res or []): items.append({"pubkey": it.get("pubkey")})
        return {
            "ok": True, "programId": program_id,
            "accountsFromIDL": idl_accounts, "usingAccountNames": {"position": pos_name},
            "count": len(items), "items": items,
            "note": "no owner supplied; showing all position pubkeys."
        }

    # owner supplied → try env offset first
    env_off = _env_owner_off()
    if env_off is not None:
        res = _rpc("getProgramAccounts", [program_id, _params_b58(disc_b58, owner_b58, env_off)])
        items = [{"pubkey": it.get("pubkey")} for it in (res or [])]
        return {
            "ok": True, "programId": program_id,
            "accountsFromIDL": idl_accounts, "usingAccountNames": {"position": pos_name},
            "usingOwnerOffset": env_off, "count": len(items), "items": items,
            "note": "owner-filter via env offset; pubkey-only fallback."
        }

    # quick guess cycle
    for off in _quick_offsets():
        try:
            res = _rpc("getProgramAccounts", [program_id, _params_b58(disc_b58, owner_b58, off)])
            items = [{"pubkey": it.get("pubkey")} for it in (res or [])]
            if items:
                return {
                    "ok": True, "programId": program_id,
                    "accountsFromIDL": idl_accounts, "usingAccountNames": {"position": pos_name},
                    "usingOwnerOffset": off, "count": len(items), "items": items,
                    "note": "owner-filter via guessed offset; set PERPS_POSITION_OWNER_OFFSET to pin."
                }
        except Exception:
            continue

    return {
        "ok": False,
        "error": "Could not find owner offset with quick guesses. "
                 "Call /api/perps/debug/owner-offset?owner=<pubkey> to probe and then set PERPS_POSITION_OWNER_OFFSET."
    }
