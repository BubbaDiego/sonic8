# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict
import time

from backend.core.cyclone import CyclonePositionService


def sync_positions_service(ctx: Any) -> Dict[str, Any]:
    """Run Cyclone positions sync before monitors and report the result."""

    dl = ctx.dl
    logger = getattr(ctx, "logger", None)
    start = time.time()
    try:
        cnt = CyclonePositionService.run_full(dl, source="sonic")
        duration = time.time() - start
        if logger:
            logger.info(
                "📊 Positions service  count %s  (%.2fs)  cycle=%s",
                cnt,
                duration,
                getattr(ctx, "cycle_id", "unknown"),
            )
        return {"ok": True, "source": "CyclonePositionService", "count": cnt, "duration": duration}
    except Exception as exc:
        duration = time.time() - start
        if logger:
            logger.exception("Cyclone positions sync failed: %s", exc)
        # Fallback to manager count if available
        try:
            mgr = getattr(dl, "positions", None)
            cnt = len(mgr.get_positions()) if mgr else 0
        except Exception:
            cnt = 0
        return {"ok": False, "source": "CyclonePositionService", "count": cnt, "duration": duration, "error": str(exc)}
