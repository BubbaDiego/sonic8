# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict

def sync_positions_service(ctx: Any) -> Dict[str, Any]:
    """
    Adapter for your positions sync (DL-backed).
    """
    dl = ctx.dl
    try:
        mod = __import__("backend.core.positions_core.position_sync_service", fromlist=["sync_positions"])
        sync_positions = getattr(mod, "sync_positions", None)
        if callable(sync_positions):
            res = sync_positions(dl)
            return {"ok": True, "source": "position_sync_service", "result": res}
    except Exception:
        pass
    # As a fallback, just report what the DB currently has
    try:
        mgr = getattr(dl, "positions", None)
        cnt = len(mgr.get_positions()) if mgr else 0
        return {"ok": True, "source": "dl.positions", "count": cnt}
    except Exception:
        return {"ok": False, "source": "dl.positions", "count": 0}
