from __future__ import annotations

from typing import Any, Dict, List


def compose_alerts_inline(state: Dict[str, Any]) -> str:
    """
    Build a brief human string:
      "Profit Monitor — pos T=50, V=150; pf ok | Liquid Monitor — BTC T=5.0%, V=3.1% ETH ok SOL ok"
    """

    parts: List[str] = []

    p = state.get("profit") or {}
    if p:
        sub: List[str] = []
        pos = p.get("position") or {}
        pf = p.get("portfolio") or {}
        if pos:
            sub.append(_profit_brief("pos", pos))
        if pf:
            sub.append(_profit_brief("pf", pf))
        if sub:
            parts.append("Profit Monitor — " + "; ".join(sub))

    liq = state.get("liquid") or []
    if isinstance(liq, list) and liq:
        sub2: List[str] = []
        for item in liq:
            sym = str(item.get("asset", "")).upper()
            d = item.get("dist_pct")
            th = item.get("threshold")
            br = bool(item.get("breach"))
            if not sym or d is None or th is None:
                continue
            if br:
                sub2.append(f"{sym} T={th:.1f}%, V={d:.1f}%")
            else:
                sub2.append(f"{sym} ok")
        if sub2:
            parts.append("Liquid Monitor — " + " ".join(sub2))

    return " | ".join(parts) if parts else "none"


def _profit_brief(label: str, node: Dict[str, Any]) -> str:
    val = node.get("value")
    thr = node.get("threshold")
    br = bool(node.get("breach"))
    if val is None or thr is None:
        return f"{label} n/a"
    if br:
        return f"{label} T={thr:.0f}, V={val:.0f}"
    return f"{label} ok"
