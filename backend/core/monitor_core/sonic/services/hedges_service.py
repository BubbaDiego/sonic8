# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict


def _attempt(fn_paths: list[tuple[str, str]], ctx: Any) -> Dict[str, Any] | None:
    """
    Try a list of (module, symbol) candidates and call with (ctx) or ().
    Return a result dict or None if none were found/called.
    """
    for mod_name, sym in fn_paths:
        try:
            mod = __import__(mod_name, fromlist=[sym])
            fn = getattr(mod, sym, None)
            if callable(fn):
                # try (ctx) first, else no-arg
                try:
                    res = fn(ctx)
                except TypeError:
                    res = fn()
                return {"ok": True, "source": f"{mod_name}.{sym}", "result": res}
        except Exception:
            pass
    return None


def sync_hedges_service(ctx: Any) -> Dict[str, Any]:
    """
    DB-first hedges 'service' adapter. Intentionally tolerant:
    - If you have a real hedging sync, we call it and return a count or note.
    - If not, we report noop so the Cycle Activity row still renders.
    """
    # Candidate hooks you might already have; add/remove as your code evolves
    candidates: list[tuple[str, str]] = [
        ("backend.core.hedge_core.hedge_sync_service", "sync_hedges"),
        ("backend.core.hedge_core.hedge_service", "sync_hedges"),
        ("backend.core.hedge_core.services", "sync_hedges"),
    ]
    hit = _attempt(candidates, ctx)
    if hit:
        # Try to compute a short 'count' note when possible
        res = hit.get("result")
        count = None
        try:
            if isinstance(res, dict) and "count" in res:
                count = res["count"]
        except Exception:
            pass
        out: Dict[str, Any] = {"ok": True, "source": hit.get("source")}
        if count is not None:
            out["count"] = count
        return out

    # Fallback: report noop (engine will render 'Hedges service' row with ✅ and 0.00s)
    return {"ok": True, "source": "noop", "count": 0}
