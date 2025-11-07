# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict

def sync_prices_service(ctx: Any) -> Dict[str, Any]:
    """
    Adapter for your existing price sync. If a first-party sync exists,
    call it here; otherwise return a no-op result.
    """
    dl = ctx.dl
    try:
        # Try a known helper if you have one
        mod = __import__("backend.core.price_core.price_sync_service", fromlist=["run_price_sync"])
        run_price_sync = getattr(mod, "run_price_sync", None)
        if callable(run_price_sync):
            res = run_price_sync(dl)
            return {"ok": True, "source": "price_sync_service", "result": res}
    except Exception:
        pass
    return {"ok": True, "source": "noop", "result": None}
