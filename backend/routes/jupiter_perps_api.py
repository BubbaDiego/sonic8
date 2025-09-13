from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.perps.markets import list_markets
from backend.services.perps.positions import list_positions
from backend.services.signer_loader import load_signer

router = APIRouter(prefix="/api/perps", tags=["perps"])


@router.get("/markets")
async def perps_markets():
    try:
        return await list_markets()
    except Exception as e:
        raise HTTPException(502, f"markets fetch failed: {e}")


@router.get("/positions")
async def perps_positions(owner: Optional[str] = Query(None, description="owner pubkey; default signer")):
    try:
        if not owner:
            owner = str(load_signer().pubkey())
        return await list_positions(owner)
    except Exception as e:
        raise HTTPException(502, f"positions fetch failed: {e}")
