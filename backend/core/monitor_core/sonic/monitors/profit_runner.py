# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict

def run_profit_monitors(ctx: Any) -> Dict[str, Any]:
    try:
        mod = __import__("backend.core.monitor_core.profit_monitor", fromlist=["run"])
        run = getattr(mod, "run", None)
        if callable(run):
            result = run(ctx.dl) if run.__code__.co_argcount == 1 else run()
            return {"ok": True, "source": "profit_monitor", "result": result}
    except Exception:
        pass
    return {"ok": True, "source": "profit_monitor", "result": None}
