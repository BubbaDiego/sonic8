# backend/routes/jupiter_perps_api.py
from __future__ import annotations

from typing import Optional, Dict

from fastapi import APIRouter, HTTPException, Query
import anyio
import base64
import hashlib
from collections import Counter

from backend.services.perps.markets import list_markets_sync
from backend.services.perps.positions import list_positions_sync
from backend.services.perps.raw_rpc import _rpc, get_program_id, get_idl_account_names

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


@router.get("/debug/discriminators")
async def perps_discriminators(limit_pages: int = 1, page_size: int = 1000):
    """
    Helius-friendly discriminator scan using getProgramAccountsV2 + dataSlice (len=8).
    We only fetch a few pages to avoid heavy requests. Returns top discriminator hex and counts.
    """
    try:
        pid = get_program_id()
        disc_counts: Counter[str] = Counter()
        pages = max(1, min(limit_pages, 5))
        for page in range(1, pages + 1):
            params = {
                "encoding": "base64",
                "dataSlice": {"offset": 0, "length": 8},
                "page": page,
                "limit": page_size
            }
            # Helius method name:
            res = _rpc("getProgramAccountsV2", [pid, params])  # will fail on non-Helius RPCs
            for it in (res or []):
                data = it.get("account", {}).get("data")
                raw = b""
                if isinstance(data, list) and data:
                    raw = base64.b64decode(data[0])
                elif isinstance(data, dict) and "encoded" in data:
                    raw = base64.b64decode(data["encoded"])
                if len(raw) >= 8:
                    disc_counts.update([raw[:8].hex()])
        top = disc_counts.most_common(15)
        return {"programId": pid, "topDiscriminators": [{"discHex": k, "count": c} for k, c in top]}
    except Exception as e:
        raise HTTPException(500, f"disc scan failed: {e}")
