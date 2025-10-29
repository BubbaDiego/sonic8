# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict

def fmt_float(v, d="—"):
    try:
        if v is None: return d
        x = float(v)
        s = f"{x:.2f}".rstrip("0").rstrip(".")
        return s
    except Exception:
        return d

def liquid_line(liq: Dict) -> str:
    srcs = liq.get("source", {})
    parts = [
        f"BTC {fmt_float(liq.get('BTC'))}",
        f"ETH {fmt_float(liq.get('ETH'))}",
        f"SOL {fmt_float(liq.get('SOL'))}",
    ]
    # If all same source, show once; else mixed
    uniq = set(srcs.values())
    src = "FILE" if "FILE" in uniq and len(uniq)==1 else ("DB" if uniq=={'DB'} else "MIXED")
    return " • ".join(parts) + f"   [{src}]"

def profit_line(prof: Dict) -> str:
    pos = prof.get("pos"); pf = prof.get("pf"); src = prof.get("source","—")
    def usd(x): 
        return "—" if x is None else f"${int(round(float(x)))}"
    return f"Single {usd(pos)} • Portfolio {usd(pf)}   [{src}]"
