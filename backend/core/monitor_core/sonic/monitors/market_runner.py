from __future__ import annotations

from typing import Any, Dict

from backend.core.market_core.market_engine import evaluate_market_alerts


def _load_prices_for_runner(dl) -> Dict[str, float]:
    prices: Dict[str, float] = {}
    mgr = getattr(dl, "prices", None)
    if mgr is None:
        return prices

    try:
        rows = mgr.get_all_prices()
    except Exception:
        return prices

    if not rows:
        return prices

    tracked_assets = {"SPX", "BTC", "ETH", "SOL", "^GSPC", "SP500"}

    for row in rows:
        if isinstance(row, dict):
            sym = (
                row.get("asset_type")
                or row.get("symbol")
                or row.get("asset")
                or row.get("ticker")
            )
            price = row.get("current_price") or row.get("price")
        else:
            sym = (
                getattr(row, "asset_type", None)
                or getattr(row, "symbol", None)
                or getattr(row, "asset", None)
            )
            price = getattr(row, "current_price", None) or getattr(row, "price", None)

        if sym is None or price is None:
            continue

        sym_str = str(sym).upper()
        if sym_str not in tracked_assets:
            continue
        if sym_str in ("^GSPC", "SP500"):
            sym_str = "SPX"

        try:
            prices[sym_str] = float(price)
        except (TypeError, ValueError):
            continue

    return prices


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
    """Sonic runner for the 'market' monitor."""

    dl = _resolve_dl(ctx)
    if dl is None:
        return {"ok": False, "error": "no data locker", "statuses": []}

    prices = _load_prices_for_runner(dl)
    return evaluate_market_alerts(dl, prices)
