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
            # normalize to statuses
            rows = []
            try:
                # expected shapes: list of dicts OR dict with assets
                if isinstance(result, list):
                    for it in result:
                        rows.append({
                            "label": it.get("label") or it.get("name") or it.get("asset"),
                            "state": it.get("state") or it.get("status") or "OK",
                            "value": it.get("distance") or it.get("value"),
                            "unit": it.get("unit") or "%",
                            **it
                        })
                elif isinstance(result, dict):
                    for k, v in result.items():
                        if isinstance(v, dict):
                            rows.append({
                                "label": v.get("label") or k,
                                "state": v.get("state") or v.get("status") or "OK",
                                "value": v.get("distance") or v.get("value"),
                                "unit": v.get("unit") or "%",
                                **v
                            })
            except Exception:
                pass
            return {"ok": True, "source": "liquid_monitor", "result": result, "statuses": rows}
    except Exception:
        pass
    return {"ok": True, "source": "liquid_monitor", "result": None, "statuses": []}
