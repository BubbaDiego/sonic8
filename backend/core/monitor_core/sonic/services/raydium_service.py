# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict

def sync_raydium_service(ctx: Any) -> Dict[str, Any]:
    """
    Adapter for your Raydium sync (NFT valuation etc).
    """
    dl = ctx.dl
    try:
        mod = __import__("backend.core.raydium_core.services.nft_valuation", fromlist=["value_owner_nfts"])
        fn = getattr(mod, "value_owner_nfts", None)
        if callable(fn):
            owner = None
            # Attempt to resolve active wallet from dl.wallets if present
            wmgr = getattr(dl, "wallets", None)
            if wmgr and hasattr(wmgr, "get_wallets"):
                try:
                    ws = wmgr.get_wallets() or []
                    for w in ws:
                        if w.get("is_active"):
                            owner = w.get("public_address") or w.get("pubkey")
                            break
                    if not owner and ws:
                        owner = ws[0].get("public_address") or ws[0].get("pubkey")
                except Exception:
                    pass
            res = fn(owner) if owner else fn(None)
            return {"ok": True, "source": "raydium.valuation", "result": res}
    except Exception:
        pass
    return {"ok": True, "source": "noop", "result": None}
