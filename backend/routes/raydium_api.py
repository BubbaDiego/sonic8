# -*- coding: utf-8 -*-
"""
Raydium NFT API
Exposes current snapshot and history of CLMM position NFTs, plus a sync trigger.

Endpoints:
  GET  /raydium/nfts?owner=...
  GET  /raydium/nfts/{mint}
  GET  /raydium/nfts/{mint}/history?limit=200
  POST /raydium/nfts/sync?owner=...&price_url=...
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.data.data_locker import DataLocker
from backend.core.raydium_core.services.nft_scanner import scan_owner_nfts
from backend.core.raydium_core.services.nft_valuation import value_owner_nfts

router = APIRouter(prefix="/raydium", tags=["raydium"])


# ---- helpers -----------------------------------------------------------------

def _active_owner(dl: DataLocker) -> Optional[str]:
    sys = getattr(dl, "system", None)
    if sys and hasattr(sys, "get_var"):
        for k in (
            "wallet.current_pubkey",
            "wallet_pubkey",
            "active_wallet_pubkey",
            "current_wallet_pubkey",
        ):
            try:
                v = sys.get_var(k)
                if isinstance(v, str) and len(v) > 30:
                    return v
            except Exception:
                pass
    return None


# ---- routes ------------------------------------------------------------------

@router.get("/nfts")
def list_nfts(owner: Optional[str] = Query(None)) -> List[dict]:
    """
    List current Raydium CLMM NFTs (valued snapshot).
    - If owner provided, scopes to that wallet.
    - Otherwise returns all known rows.
    """
    dl = DataLocker.get_instance()
    mgr = getattr(dl, "raydium", None)
    if not mgr:
        return []
    return mgr.get_by_owner(owner) if owner else mgr.get_positions()


@router.get("/nfts/{mint}")
def get_nft(mint: str) -> dict:
    dl = DataLocker.get_instance()
    mgr = getattr(dl, "raydium", None)
    if not mgr:
        raise HTTPException(status_code=404, detail="NFT not found")
    row = mgr.get_by_mint(mint)
    if not row:
        raise HTTPException(status_code=404, detail="NFT not found")
    return row


@router.get("/nfts/{mint}/history")
def get_nft_history(mint: str, limit: int = Query(200, ge=1, le=5000)) -> List[dict]:
    dl = DataLocker.get_instance()
    mgr = getattr(dl, "raydium", None)
    if not mgr:
        return []
    return mgr.history_for(mint, limit=limit)


@router.post("/nfts/sync")
def sync_nfts(
    owner: Optional[str] = Query(None, description="Wallet public key (base58)"),
    price_url: Optional[str] = Query(None, description="Override Jupiter price URL (optional)"),
) -> dict:
    """
    Trigger a discovery + valuation pass for the owner's CLMM NFTs.
    Returns counts and an updated total USD for the owner.
    """
    dl = DataLocker.get_instance()
    resolved_owner = owner or _active_owner(dl)
    if not resolved_owner:
        raise HTTPException(
            status_code=400,
            detail="owner is required (or set wallet.current_pubkey in system vars)",
        )

    scanned = scan_owner_nfts(resolved_owner, dl=dl)     # discover (writes to DB)
    valued = value_owner_nfts(resolved_owner, price_url=price_url)  # value (writes to DB)
    total = getattr(dl, "raydium", None).get_total_usd(resolved_owner) if getattr(dl, "raydium", None) else 0.0

    return {
        "owner": resolved_owner,
        "scanned": scanned,
        "valued": valued,
        "total_usd": total,
        "status": "ok",
    }
