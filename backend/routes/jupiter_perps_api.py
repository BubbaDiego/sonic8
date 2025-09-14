# backend/routes/jupiter_perps_api.py
from __future__ import annotations

from typing import Optional, Dict

from fastapi import APIRouter, HTTPException, Query
import anyio

from backend.services.perps.markets import list_markets_sync
from backend.services.perps.positions import list_positions_sync
from backend.services.perps.raw_rpc import _rpc, get_program_id, get_idl_account_names
from backend.services.perps.config import get_disc, get_account_name

# tiny base58 encoder (same as service)
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
    leading = 0
    for ch in b:
        if ch == 0: leading += 1
        else: break
    return (_B58_ALPH[0] * leading) + res


router = APIRouter(prefix="/api/perps", tags=["perps"])


@router.get("/markets")
async def perps_markets():
    try:
        return await anyio.to_thread.run_sync(list_markets_sync)
    except Exception as e:
        raise HTTPException(502, f"markets fetch failed: {e}")


@router.get("/positions")
async def perps_positions(owner: Optional[str] = Query(None, description="owner pubkey")):
    try:
        return await anyio.to_thread.run_sync(list_positions_sync, owner)
    except Exception as e:
        raise HTTPException(502, f"positions fetch failed: {e}")


@router.get("/positions/detailed")
async def perps_positions_detailed(owner: str, limit: int = 50):
    """
    Decode fields for owner positions (size, entry, mark, est PnL).
    Uses v2 decoder (never throws). Requires PERPS_POSITION_OWNER_OFFSET.
    """
    from backend.services.perps.detail import fetch_positions_detailed_v2
    import anyio
    try:
        # run sync wrapper in a worker thread
        return await anyio.to_thread.run_sync(fetch_positions_detailed_v2, owner, limit)
    except Exception as e:
        # We shouldn't hit this, but keep a guard
        return {"ok": False, "version": "v2", "error": f"unexpected route error: {e}"}


@router.get("/debug/idl")
async def perps_idl_debug():
    try:
        pid = get_program_id()
        names = get_idl_account_names()
        return {"programId": pid, "accounts": names}
    except Exception as e:
        raise HTTPException(500, f"idl debug failed: {e}")


@router.get("/debug/owner-offset")
async def perps_owner_offset(owner: str, start: int = 8, stop: int = 192, step: int = 1, sample: int = 1):
    """
    Probe the correct byte offset of the `owner` field in Position account:
    Tries memcmp(discriminator) AND memcmp(owner@offset) across a small range
    and returns the first offsets that yield results.

    Example: /api/perps/debug/owner-offset?owner=YourPubkey&start=8&stop=192&step=4
    """
    try:
        pid = get_program_id()
        pos_name = get_account_name("position", "Position")
        disc_b58 = _b58encode(get_disc("position", pos_name))

        hits = []
        for off in range(max(0, start), max(0, stop), max(1, step)):
            params = {
                "encoding": "base64",
                "commitment": "confirmed",
                "filters": [
                    {"memcmp": {"offset": 0, "bytes": disc_b58}},
                    {"memcmp": {"offset": off, "bytes": owner}}
                ]
            }
            res = await anyio.to_thread.run_sync(_rpc, "getProgramAccounts", [pid, params])
            count = len(res or [])
            if count > 0:
                hits.append({"offset": off, "count": count})
                if sample == 1:
                    break

        return {
            "programId": pid,
            "positionAccountName": pos_name,
            "owner": owner,
            "hits": hits,
            "note": ("Set PERPS_POSITION_OWNER_OFFSET=<offset> to pin it. "
                     "Then /api/perps/positions will return only your positions.")
        }
    except Exception as e:
        raise HTTPException(500, f"owner offset probe failed: {e}")
