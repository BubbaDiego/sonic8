from __future__ import annotations

from typing import Any, Dict

from backend.core.market_core.market_engine import evaluate_market_alerts


def _resolve_dl(ctx: Any):
    if ctx is None:
        return None
    dl = getattr(ctx, "dl", None)
    if dl is not None:
        return dl
    if isinstance(ctx, dict):
        return ctx.get("dl")
    return None


def run_market_monitors(ctx: Any) -> Dict[str, Any]:
    """
    Sonic runner for the 'market' monitor.

    Codex: adapt the price query to your actual DL prices API.
    The intent is to produce { "BTC": 12345.0, "ETH": ..., "SPX": ... }.
    """
    dl = _resolve_dl(ctx)
    if dl is None:
        return {"ok": False, "error": "no data locker", "statuses": []}

    # Example assuming dl.prices.select_all() returns rows with symbol/price.
    rows = dl.prices.select_all()
    prices: Dict[str, float] = {}
    for row in rows:
        sym = row.get("symbol") or row.get("asset") or row.get("ticker")
        if sym is None:
            continue
        prices[str(sym)] = float(row.get("price") or 0.0)

    return evaluate_market_alerts(dl, prices)
