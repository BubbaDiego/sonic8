# backend/routes/jupiter_perps_api.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
import anyio

from backend.services.perps.markets import list_markets_sync
from backend.services.perps.positions import list_positions_sync
from backend.services.perps.raw_rpc import get_program_id, get_idl_account_names, _rpc

router = APIRouter(prefix="/api/perps", tags=["perps"])


@router.get("/markets")
async def perps_markets():
    try:
        return await anyio.to_thread.run_sync(list_markets_sync)
    except Exception as e:
        raise HTTPException(502, f"markets fetch failed: {e}")


@router.get("/positions")
async def perps_positions(owner: Optional[str] = Query(None, description="owner pubkey; ignored in fallback")):
    try:
        return await anyio.to_thread.run_sync(list_positions_sync, owner)
    except Exception as e:
        raise HTTPException(502, f"positions fetch failed: {e}")


@router.get("/debug/idl")
async def perps_idl_debug():
    try:
        pid = get_program_id()
        names = get_idl_account_names()
        return {"programId": pid, "accounts": names}
    except Exception as e:
        raise HTTPException(500, f"idl debug failed: {e}")


@router.get("/debug/raw")
async def perps_raw(limit: int = 5):
    """Raw sample from getProgramAccounts to verify RPC shape."""
    try:
        pid = get_program_id()
        res = await anyio.to_thread.run_sync(_rpc, "getProgramAccounts", [pid, {"encoding": "base64"}])
        rows = res or []
        return {"programId": pid, "count": len(rows), "sample": rows[:max(0, min(limit, len(rows)))]}
    except Exception as e:
        raise HTTPException(500, f"raw debug failed: {e}")
