from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from solders.pubkey import Pubkey

from backend.services.perps.client import get_perps_program
from backend.services.perps.config import get_disc, get_account_name
from backend.services.perps.raw_rpc import _rpc, get_program_id
from backend.services.perps.compute import extract_fields, get_mark_price_usdc, est_pnl_usd

# base58 encoder (same as others)
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def _b58enc(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = _B58[0] if n == 0 else ""
    out = []
    while n:
        n, r = divmod(n, 58)
        out.append(_B58[r])
    s += "".join(reversed(out))
    z = 0
    for ch in b:
        if ch == 0: z += 1
        else: break
    return (_B58[0] * z) + s


def _owner_off_from_env() -> Optional[int]:
    v = (os.getenv("PERPS_POSITION_OWNER_OFFSET") or "").strip()
    if not v: return None
    try: return int(v)
    except Exception: return None


def fetch_positions_detailed(owner: str, limit: int = 100) -> Dict[str, Any]:
    """
    Filter by (discriminator + owner@offset) then decode each Position account with AnchorPy.
    Returns size, entry, mark, est PnL.
    """
    off = _owner_off_from_env()
    if off is None:
        return {"ok": False, "error": "PERPS_POSITION_OWNER_OFFSET not set. Probe it then set env."}

    program, client = None, None
    try:
        program, client = None, None
        program, client = (await_get_perps_program_sync())  # we wrap async→sync below
    except Exception as e:
        return {"ok": False, "error": f"IDL/program init failed: {e}"}

    try:
        pos_name = get_account_name("position", "Position")
        disc_b58 = _b58enc(get_disc("position", pos_name))
        params = {
            "encoding": "base64",
            "commitment": "confirmed",
            "filters": [
                {"memcmp": {"offset": 0, "bytes": disc_b58}},
                {"memcmp": {"offset": int(off), "bytes": owner}}
            ],
            "limit": int(limit)
        }
        pid = get_program_id()
        res = _rpc("getProgramAccounts", [pid, params])
        pubs = [r.get("pubkey") for r in (res or []) if r.get("pubkey")]

        out: List[Dict[str, Any]] = []
        # Decode each via program.account[Position].fetch(pubkey)
        for pk in pubs:
            try:
                acc = program.account[pos_name]
                obj = acc.fetch(Pubkey.from_string(pk))  # AnchorPy returns dataclass-ish
                d = obj.__dict__ if hasattr(obj, "__dict__") else obj
                fields = extract_fields(d)
                mark = get_mark_price_usdc(fields["baseMint"])
                pnl = est_pnl_usd(fields["side"], fields["sizeUi"], fields["entryPx"], mark)
                out.append({
                    "pubkey": pk,
                    "side": fields["side"],
                    "size": fields["sizeUi"],
                    "entry": fields["entryPx"],
                    "mark": mark,
                    "pnlUsd": pnl,
                })
            except Exception as e:
                out.append({"pubkey": pk, "error": f"decode failed: {e}"})

        return {"ok": True, "count": len(out), "owner": owner, "items": out}
    finally:
        try:
            if client: client.close()
        except Exception:
            pass


# ---------- small util: run get_perps_program() sync ----------
def await_get_perps_program_sync():
    """
    AnchorPy client function is async; run it synchronously for the route context.
    """
    import anyio
    async def _run():
        return await get_perps_program()
    return anyio.run(_run)
