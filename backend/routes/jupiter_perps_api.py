from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.services.perps.markets import list_markets
from backend.services.perps.positions import list_positions
from backend.services.perps.client import get_perps_program
from backend.services.perps.util import idl_account_names
from backend.services.signer_loader import load_signer


router = APIRouter(prefix="/api/perps", tags=["perps"])


@router.get("/markets")
async def perps_markets():
    try:
        return await list_markets()
    except Exception as e:
        raise HTTPException(502, f"markets fetch failed: {e}")


@router.get("/positions")
async def perps_positions(
    owner: Optional[str] = Query(None, description="owner pubkey; default signer")
):
    try:
        if not owner:
            owner = str(load_signer().pubkey())
        return await list_positions(owner)
    except Exception as e:
        raise HTTPException(502, f"positions fetch failed: {e}")


@router.get("/debug/idl")
async def perps_idl_debug():
    """
    Quick probe of account names + program id from the vendored IDL.
    Helps confirm we're decoding the right types.
    """
    try:
        program, client = await get_perps_program()
        try:
            names = idl_account_names(program)
            return {
                "programId": str(program.program_id),
                "accounts": names,
                "instructions": [
                    ix.name for ix in (program.idl.instructions or [])
                ],
            }
        finally:
            await client.close()
    except Exception as e:
        raise HTTPException(500, f"idl debug failed: {e}")
