# Full file: minimal FastAPI router for GMX
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from backend.core.gmx_core.services import gmx_service

router = APIRouter(prefix="/gmx", tags=["gmx"])


@router.get("/health")
def gmx_health(cluster: str = Query("mainnet"), signer_path: Optional[str] = None):
    return gmx_service.get_health(cluster=cluster, signer_path=signer_path)


@router.get("/markets")
def gmx_markets(cluster: str = Query("mainnet"), signer_path: Optional[str] = None):
    return {"markets": gmx_service.get_markets(cluster=cluster, signer_path=signer_path)}


@router.get("/positions")
def gmx_positions(cluster: str = Query("mainnet"), signer_path: Optional[str] = None):
    return {"positions": gmx_service.get_positions(cluster=cluster, signer_path=signer_path)}
