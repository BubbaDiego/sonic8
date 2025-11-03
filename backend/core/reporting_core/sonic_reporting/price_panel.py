from __future__ import annotations
from typing import Any, Mapping

ASSETS = ("BTC", "ETH", "SOL")
ASSET_ICON = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}


def _abbr(n: float | None) -> str:
    if n is None:
        return "—"
    try:
        x = float(n)
    except Exception:
        return "—"
    units = [(1_000_000_000, "b"), (1_000_000, "m"), (1_000, "k")]
    for base, suffix in units:
        if abs(x) >= base:
            return f"{x/base:.1f}{suffix}"
    # show INT if >=100, else two decimals
    return f"{x:.0f}" if abs(x) >= 100 else f"{x:.2f}"


def _get_prices_from_csum(csum: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(csum, Mapping):
        return {}
    prices = csum.get("prices") or {}
    if isinstance(prices, Mapping):
        return {k.upper(): v for k, v in prices.items() if isinstance(v, Mapping)}
    return {}


def _find_prices_fallback(dl: Any) -> dict[str, dict[str, Any]]:
    """
    Best effort to find a dict like:
      {"BTC": {"current": float, "previous": float, "checked": "str?"}, ...}
    """
    if not dl:
        return {}
    # Common places in the app where recent prices might live
    for attr in ("cache", "market", "price", "prices"):
        node = getattr(dl, attr, None)
        if isinstance(node, dict):
            # try the dict as-is
            probe = {}
            for k in ASSETS:
                d = node.get(k) if isinstance(node.get(k), dict) else None
                if d:
                    probe[k] = {
                        "current": d.get("current") or d.get("last") or d.get("price"),
                        "previous": d.get("previous"),
                        "checked": d.get("checked") or d.get("ts"),
                    }
            if probe:
                return probe
        # object with attributes
        for name in ("prices", "last_prices", "latest", "price_cache"):
            sub = getattr(node, name, None)
            if isinstance(sub, dict):
                probe = {}
                for k in ASSETS:
                    d = sub.get(k) if isinstance(sub.get(k), dict) else None
                    if d:
                        probe[k] = {
                            "current": d.get("current") or d.get("last") or d.get("price"),
                            "previous": d.get("previous"),
                            "checked": d.get("checked") or d.get("ts"),
                        }
                if probe:
                    return probe
    return {}


def _render_table(rows: list[list[str]]) -> None:
    if not rows:
        print(" (no rows)")
        return
    # simple proportional table
    widths = [max(len(str(r[c])) for r in rows) for c in range(len(rows[0]))]
    for i, row in enumerate(rows):
        print(" " + "  ".join(str(col).ljust(widths[idx]) for idx, col in enumerate(row)))
        if i == 0:
            print()


def render(dl=None, csum=None, **_):
    print("\n 💰 Prices\n")
    # Try csum first (preferred), fallback to dl
    px = _get_prices_from_csum(csum)
    if not px:
        px = _find_prices_fallback(dl)

    header = ["Asset", "Current", "Previous", "Δ", "Δ%", "Checked"]
    out = [header]
    for sym in ASSETS:
        icon = ASSET_ICON.get(sym, "•")
        d = px.get(sym, {})
        cur = d.get("current")
        prev = d.get("previous")
        checked = d.get("checked") or "—"
        if cur is None and prev is None and sym not in px:
            # show bare asset if we truly found nothing
            out.append([f"{icon} {sym}", "—", "—", "—", "—", "(—)"])
            continue
        # compute deltas if both exist
        if cur is not None and prev is not None:
            try:
                delta = float(cur) - float(prev)
                pct = (delta / float(prev) * 100.0) if float(prev) != 0 else 0.0
                d_txt = _abbr(delta)
                p_txt = f"{pct:.2f}%"
            except Exception:
                d_txt, p_txt = "—", "—"
        else:
            d_txt, p_txt = "—", "—"
        out.append([f"{icon} {sym}", _abbr(cur), _abbr(prev), d_txt, p_txt, f"({checked})"])

    _render_table(out)
