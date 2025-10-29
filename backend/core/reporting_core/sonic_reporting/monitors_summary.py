# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from .writer import write_line

def render(csum: Dict[str, Any]) -> None:
    # Minimal; keep or remove based on preference
    for name in ("price_monitor","market_monitor","profit_monitor","liquid_monitor"):
        try:
            info = (csum.get("monitors") or {}).get(name) or {}
            state = "fresh" if info.get("fresh") else "done"
            dur = info.get("dur", 0.6)
            write_line(f"   {name} ({dur:.2f}s)  — {state}")
        except Exception:
            pass
