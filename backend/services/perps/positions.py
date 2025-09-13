# backend/services/perps/positions.py
from __future__ import annotations

import os
import hashlib
from typing import Dict, List, Optional

from backend.services.perps.raw_rpc import _rpc, get_program_id, get_idl_account_names
from backend.services.perps.config import get_disc, get_account_name

# ---------- base58 (tiny encoder; no extra dependency) ----------
_B58_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def _b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    if n == 0:
        res = _B58_ALPH[0]
    else:
        chars = []
        while n:
            n, r = divmod(n, 58)
            chars.append(_B58_ALPH[r])
        res = "".join(reversed(chars))
    # preserve leading zeros
    leading = 0
    for ch in b:
        if ch == 0: leading += 1
        else: break
    return (_B58_ALPH[0] * leading) + res


def _filter_params_b58(disc_b58: str, owner_b58: Optional[str], owner_offset: Optional[int]) -> dict:
    f = [{"memcmp": {"offset": 0, "bytes": disc_b58}}]
    if owner_b58 and owner_offset is not None:
        f.append({"memcmp": {"offset": int(owner_offset), "bytes": owner_b58}})
    return {
        "encoding": "base64",
        "commitment": "confirmed",
        "filters": f
    }


def _env_owner_offset() -> Optional[int]:
    val = (os.getenv("PERPS_POSITION_OWNER_OFFSET") or "").strip()
    if not val:
        return None
    try:
        return int(val)
    except Exception:
        return None


def _quick_guess_offsets() -> List[int]:
    """
    Small set of common offsets (after 8-byte discriminator).
    This avoids brute forcing hundreds of calls.
    You can refine by setting PERPS_POSITION_OWNER_OFFSET once we confirm.
    """
    base = 8  # always after discriminator
    return [base + x for x in (0, 32, 40, 48, 64, 72, 80, 96, 104, 112, 128, 136, 144)]


def list_positions_sync(owner: Optional[str]) -> Dict[str, object]:
    """
    Return ONLY pubkeys for Position accounts, filtering by owner if possible.
    Priority for owner offset:
      1) PERPS_POSITION_OWNER_OFFSET (env)
      2) quick guess list (stop on first non-zero)
      3) fall back to 'all positions' if owner not provided
    """
    program_id = get_program_id()
    idl_accounts = get_idl_account_names()

    pos_name_cfg = get_account_name("position", "Position")
    pos_disc = get_disc("position", pos_name_cfg)
    pos_disc_b58 = _b58encode(pos_disc)

    owner_b58 = (owner or "").strip() or None

    # If no owner provided, return all positions (still filtered by discriminator)
    if not owner_b58:
        items: List[dict] = []
        try:
            res = _rpc("getProgramAccounts", [program_id, _filter_params_b58(pos_disc_b58, None, None)])
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
            "note": "no owner supplied; showing all position accounts (pubkeys only)."
        }

    # Owner provided → try env offset first
    env_off = _env_owner_offset()
    if env_off is not None:
        items: List[dict] = []
        try:
            res = _rpc("getProgramAccounts", [program_id, _filter_params_b58(pos_disc_b58, owner_b58, env_off)])
            for it in (res or []):
                items.append({"pubkey": it.get("pubkey")})
            return {
                "ok": True,
                "programId": program_id,
                "accountsFromIDL": idl_accounts,
                "usingAccountNames": {"position": pos_name_cfg},
                "usingOwnerOffset": env_off,
                "count": len(items),
                "items": items,
                "note": "owner-filtered via env offset; pubkey-only fallback."
            }
        except Exception as e:
            return {"ok": False, "error": f"Position GPA (env offset={env_off}) failed: {e}"}

    # Quick guess cycle (few calls only)
    for off in _quick_guess_offsets():
        try:
            res = _rpc("getProgramAccounts", [program_id, _filter_params_b58(pos_disc_b58, owner_b58, off)])
            items = [{"pubkey": it.get("pubkey")} for it in (res or [])]
            if items:  # Found a working offset!
                return {
                    "ok": True,
                    "programId": program_id,
                    "accountsFromIDL": idl_accounts,
                    "usingAccountNames": {"position": pos_name_cfg},
                    "usingOwnerOffset": off,
                    "count": len(items),
                    "items": items,
                    "note": "owner-filtered via guessed offset; set PERPS_POSITION_OWNER_OFFSET to pin."
                }
        except Exception:
            continue

    # Nothing hit → ask user to run the dedicated probe endpoint (/api/perps/debug/owner-offset)
    return {
        "ok": False,
        "error": "Could not find owner offset via quick guesses. "
                 "Call /api/perps/debug/owner-offset?owner=<pubkey> to probe and then set PERPS_POSITION_OWNER_OFFSET."
    }
