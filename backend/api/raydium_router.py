from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.core.raydium_core.raydium_core import RaydiumCore
from backend.core.wallet_core.wallet_core import WalletCore  # Sonic existing wallet core

router = APIRouter(prefix="/raydium", tags=["raydium"])


# Core instances are lightweight; create on-demand
def _core() -> RaydiumCore:
    return RaydiumCore(
        rpc_url=os.getenv("RPC_URL"),
        raydium_api_base=os.getenv("RAYDIUM_API_BASE"),  # default handled in RaydiumDataLayer
    )


@router.get("/me/balances")
def my_balances(include_zero: bool = Query(False, description="Include zero balances"), enrich_meta: bool = True):
    """
    Get balances for the default Sonic wallet (WALLET_SECRET_BASE64), headless.
    """
    try:
        me = WalletCore().get_default_public_key_base58()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"WalletCore error: {e}")
    bal = _core().get_wallet_balances(me, include_zero=include_zero, enrich_meta=enrich_meta)
    return bal.model_dump()


@router.get("/wallet/{owner}/balances")
def wallet_balances(owner: str, include_zero: bool = Query(False), enrich_meta: bool = True):
    """
    Get balances for any wallet address (base58), headless.
    """
    try:
        bal = _core().get_wallet_balances(owner, include_zero=include_zero, enrich_meta=enrich_meta)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))
    return bal.model_dump()


@router.get("/token-list")
def token_list():
    """
    Fetch Raydium token list (public API v3).
    """
    try:
        items = _core().get_token_list()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Raydium API error: {e}")
    return [t.model_dump() for t in items]


@router.get("/pools")
def pool_list(
    page: Optional[int] = None,
    pageSize: Optional[int] = None,
    mint1: Optional[str] = None,
    mint2: Optional[str] = None,
):
    """
    Fetch Raydium pool list (or filter by mints) from public API v3.
    """
    c = _core()
    try:
        if mint1:
            return c.fetch_pool_by_mints(mint1, mint2, page=page, pageSize=pageSize)
        return c.get_pool_list(page=page, pageSize=pageSize)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Raydium API error: {e}")
