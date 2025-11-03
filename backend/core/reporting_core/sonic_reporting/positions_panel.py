from __future__ import annotations
from typing import Any, Mapping, Sequence

ASSETS = ("BTC", "ETH", "SOL")
ASSET_ICON = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}


def _abbr_money(n: float | None) -> str:
    if n is None:
        return "$0.00"
    try:
        x = float(n)
    except Exception:
        return "$0.00"
    s = "-" if x < 0 else ""
    x = abs(x)
    units = [(1_000_000_000, "b"), (1_000_000, "m"), (1_000, "k")]
    for base, suffix in units:
        if x >= base:
            return f"{s}${x/base:.1f}{suffix}"
    return f"{s}${x:.2f}"


def _pct(n: float | None) -> str:
    if n is None:
        return "—"
    try:
        return f"{float(n):.2f}%"
    except Exception:
        return "—"


def _get(rows: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for k in keys:
        if k in rows:
            return rows[k]
    return None


def _get_num(rows: Mapping[str, Any], keys: Sequence[str]) -> float | None:
    v = _get(rows, keys)
    try:
        return float(v)
    except Exception:
        return None


def _symbol_of(r: Mapping[str, Any]) -> str | None:
    v = _get(r, ("asset", "symbol", "coin", "ticker"))
    if isinstance(v, str) and v:
        return v.upper().strip()
    return None


def _side_of(r: Mapping[str, Any]) -> str:
    v = _get(r, ("side", "position_side", "pos_side"))
    if isinstance(v, str):
        v = v.upper().strip()
        if v in ("LONG", "SHORT"):
            return v
    # try sign of size
    qty = _get_num(r, ("qty", "size", "notional", "amount"))
    return "SHORT" if (qty is not None and qty < 0) else "LONG"


def _liq_of(r: Mapping[str, Any]) -> float | None:
    # flat or nested
    for k in ("liq", "liq_dist", "liquidation", "liquidation_distance", "liq_pct"):
        if k in r:
            try:
                return float(r[k])
            except Exception:
                pass
    meta = r.get("risk") or r.get("meta") or {}
    if isinstance(meta, Mapping):
        for k in ("liq", "liq_dist", "liquidation"):
            try:
                return float(meta.get(k))
            except Exception:
                pass
    return None


def _extract_positions_from_csum(csum: Mapping[str, Any] | None) -> list[dict]:
    if not isinstance(csum, Mapping):
        return []
    rows = csum.get("positions") or csum.get("pos_rows") or []
    return rows if isinstance(rows, list) else []


def _extract_positions_from_dl(dl: Any) -> list[dict]:
    if not dl:
        return []
    # Try a few common shelves on DataLocker
    for attr in ("positions", "portfolio", "cache"):
        node = getattr(dl, attr, None)
        if not node:
            continue
        # property/lists
        for name in ("active", "active_positions", "positions", "last_positions", "snapshot"):
            got = getattr(node, name, None)
            if isinstance(got, list) and got:
                return [g if isinstance(g, dict) else getattr(g, "__dict__", {}) for g in got]
        # callables
        for name in ("active", "active_positions", "positions", "last_positions", "snapshot"):
            m = getattr(node, name, None)
            if callable(m):
                try:
                    got = m()
                except Exception:
                    got = None
                if isinstance(got, list) and got:
                    return [g if isinstance(g, dict) else getattr(g, "__dict__", {}) for g in got]
    return []


def _render_table(rows: list[list[str]]) -> None:
    if not rows:
        print(" (no rows)")
        return
    widths = [max(len(str(r[c])) for r in rows) for c in range(len(rows[0]))]
    for i, row in enumerate(rows):
        print(" " + "  ".join(str(col).ljust(widths[idx]) for idx, col in enumerate(row)))
        if i == 0:
            print()


def render(dl=None, csum=None, **_):
    print("\n  ---------------------- 📈  Positions  ----------------------")
    rows = _extract_positions_from_csum(csum)
    if not rows:
        rows = _extract_positions_from_dl(dl)

    header = ["Asset", "Side", "Value", "PnL", "Lev", "Liq", "Travel"]
    out = [header]

    total_value = 0.0
    total_pnl = 0.0
    long_value = 0.0
    short_value = 0.0
    count = 0

    if not rows:
        out.append(["-", "-", "-", "-", "-", "-", "-"])
        _render_table(out)
        print("                  $0.00      $0.00        -                 -")
        return

    for r in rows:
        sym = _symbol_of(r) or "-"
        icon = ASSET_ICON.get(sym, "•")
        side = _side_of(r)

        value = _get_num(r, ("value", "usd_value", "notional_usd", "notional"))
        pnl = _get_num(r, ("pnl", "pnl_usd", "profit", "unrealized_pnl"))
        lev = _get_num(r, ("lev", "leverage", "x"))
        liq = _liq_of(r)
        travel = _get_num(r, ("travel", "move_pct", "move"))

        out.append([
            f"{icon} {sym}",
            side,
            _abbr_money(value),
            _abbr_money(pnl),
            f"{lev:.2f}×" if lev is not None else "—",
            f"{liq:.2f}" if liq is not None else "—",
            _pct(travel),
        ])

        # totals
        if value is not None:
            total_value += value
            if side == "LONG":
                long_value += value
            else:
                short_value += value
        if pnl is not None:
            total_pnl += pnl
        count += 1

    _render_table(out)

    # Totals row (single-line, not a separate section)
    total_line = f"Totals:             {_abbr_money(total_value):>8}   {_abbr_money(total_pnl):>8}        -                 -"
    print(total_line)
    print(f"Count {count}  Gross {_abbr_money(abs(long_value) + abs(short_value))}  Net {_abbr_money(total_value)}  Long {_abbr_money(long_value)} / Short {_abbr_money(short_value)}")
