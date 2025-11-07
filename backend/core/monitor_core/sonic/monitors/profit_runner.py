# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict

def run_profit_monitors(ctx: Any) -> Dict[str, Any]:
    try:
        mod = __import__("backend.core.monitor_core.profit_monitor", fromlist=["run"])
        run = getattr(mod, "run", None)
        if callable(run):
            result = run(ctx.dl) if run.__code__.co_argcount == 1 else run()
            rows = []
            # Normalize common shapes from your profit monitor
            try:
                if isinstance(result, list):
                    for it in result:
                        rows.append({
                            "label": it.get("label") or it.get("name") or "Profit",
                            "state": it.get("state") or it.get("status") or "OK",
                            "value": it.get("pnl") or it.get("pnl_usd") or it.get("value"),
                            "unit": it.get("unit") or "USD",
                            **it
                        })
                elif isinstance(result, dict):
                    rows.append({
                        "label": result.get("label") or "Profit",
                        "state": result.get("state") or result.get("status") or "OK",
                        "value": result.get("pnl") or result.get("pnl_usd") or result.get("value"),
                        "unit": result.get("unit") or "USD",
                        **result
                    })
            except Exception:
                pass
            return {"ok": True, "source": "profit_monitor", "result": result, "statuses": rows}
    except Exception:
        pass
    return {"ok": True, "source": "profit_monitor", "result": None, "statuses": []}
