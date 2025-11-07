# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict

def run_liquid_monitors(ctx: Any) -> Dict[str, Any]:
    """
    Wrap existing liquid monitors (BTC/ETH/SOL) if available.
    Return a structured dict for the ledger + console reporters.
    """
    try:
        mod = __import__("backend.core.monitor_core.liquid_monitor", fromlist=["run"])
        run = getattr(mod, "run", None)
        if callable(run):
            result = run(ctx.dl) if run.__code__.co_argcount == 1 else run()
            return {"ok": True, "source": "liquid_monitor", "result": result}
    except Exception:
        pass
    return {"ok": True, "source": "liquid_monitor", "result": None}
