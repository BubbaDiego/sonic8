# positions_panel.py — FULL REPLACEMENT
# Borderless table; title matches Prices; asset icons.
# Value column now shows SIZE as abbreviated counts (e.g., 1.53k).
# Totals row: colored for distinction; PnL keeps red/green; Lev/Liq/Travel are size-weighted avgs.
# Sequencer contract: render(dl, csum, default_json_path=None)

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple
from dataclasses import is_dataclass, asdict

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.measure import Measurement


# --------------------- Small utils ---------------------

def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _abbr_count(v: Optional[float]) -> str:
    """Abbreviate a plain number (no $): 1538.68 -> 1.54k."""
    if v is None:
        return "-"
    try:
        n = float(v)
    except Exception:
        return str(v)
    a = abs(n)
    if a >= 1_000_000_000:
        return f"{n/1_000_000_000:.2f}b"
    if a >= 1_000_000:
        return f"{n/1_000_000:.2f}m"
    if a >= 1_000:
        return f"{n/1_000:.2f}k"
    return f"{n:.2f}"


def _abbr_usd(v: Optional[float]) -> str:
    if v is None:
        return "-"
    try:
        n = float(v)
    except Exception:
        return str(v)
    a = abs(n)
    if a >= 1_000_000_000: return f"${n/1_000_000_000:,.1f}b"
    if a >= 1_000_000:     return f"${n/1_000_000:,.1f}m"
    if a >= 1_000:         return f"${n/1_000:,.1f}k"
    return f"${n:,.2f}"


def _fmt_pnl(amount: Optional[float], pct: Optional[float]) -> Text:
    if amount is None and pct is None:
        return Text("-")
    parts = []
    if amount is not None:
        parts.append(_abbr_usd(amount))
    if pct is not None:
        sign = "+" if pct > 0 else ""
        parts.append(f"{sign}{pct:.2f}%")
    txt = " ".join(parts)
    style = "green" if (amount or 0) > 0 or (pct or 0) > 0 else ("red" if (amount or 0) < 0 or (pct or 0) < 0 else "")
    return Text(txt, style=style)


def _percent_text(v: Any) -> str:
    f = _to_float(v)
    return f"{f:.2f}%" if f is not None else "-"


def _as_list(obj: Any) -> List[Any]:
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, dict)):
        return list(obj)
    return [obj]


# --------------------- Dict materialization & fuzzy mapping ---------------------

def _to_dictish(x: Any) -> Dict[str, Any]:
    """Turn arbitrary objects into a dict for key-based matching."""
    if x is None:
        return {}
    if isinstance(x, dict):
        return dict(x)
    # pydantic v2
    try:
        if hasattr(x, "model_dump"):
            return x.model_dump()  # type: ignore[attr-defined]
    except Exception:
        pass
    # pydantic v1
    try:
        if hasattr(x, "dict"):
            return x.dict()  # type: ignore[attr-defined]
    except Exception:
        pass
    # dataclass
    try:
        if is_dataclass(x):
            return asdict(x)
    except Exception:
        pass
    # common "to_dict"
    try:
        if hasattr(x, "to_dict"):
            return x.to_dict()  # type: ignore[attr-defined]
    except Exception:
        pass
    # fallback to __dict__
    try:
        return dict(vars(x))
    except Exception:
        return {}


def _find_key(d: Dict[str, Any], candidates: List[str]) -> Optional[str]:
    """Return the first exact or fuzzy key match (case-insensitive, substring)."""
    if not d:
        return None
    lower_map = {k.lower(): k for k in d.keys()}
    # exact first
    for c in candidates:
        lc = c.lower()
        if lc in lower_map:
            return lower_map[lc]
    # then substring fuzzy
    for c in candidates:
        lc = c.lower()
        for lk, original in lower_map.items():
            if lc in lk:
                return original
    return None


CANDIDATES = {
    "asset":  ["asset", "asset_type", "symbol", "token", "market", "pair", "name"],
    "side":   ["side", "position_type", "direction", "pos_side"],
    "size":   ["size", "qty", "quantity", "contracts", "amount", "base_size", "position_size"],
    "value":  ["value", "usd_value", "value_usd", "notional_usd", "notional", "size_usd", "position_value"],
    "pnl_usd":["pnl_after_fees_usd", "pnl_usd", "unrealized_pnl", "u_pnl", "profit_usd"],
    "pnl_pct":["pnl_pct", "unrealized_pnl_pct", "roe", "return_pct", "pnl_percent"],
    "lev":    ["leverage", "lev", "leverage_x"],
    "liq":    ["liquidation_price", "liq_price", "liq"],
    "travel": ["travel_percent", "travel_pct", "travel", "move_pct", "change_pct"],
}


def _pick(d: Dict[str, Any], name: str) -> Any:
    k = _find_key(d, CANDIDATES[name])
    return d[k] if k is not None else None


def _normalize_row_any(obj: Any) -> Dict[str, Any]:
    d = _to_dictish(obj)

    raw_side = str(_pick(d, "side") or "-").lower()
    if raw_side not in ("long", "short", "-"):
        if raw_side.startswith("l"): raw_side = "long"
        elif raw_side.startswith("s"): raw_side = "short"

    return {
        "asset": str(_pick(d, "asset") or "-"),
        "side": raw_side,
        "size": _to_float(_pick(d, "size")),
        # keep USD notional available for totals fallback if size missing
        "usd_value": _to_float(_pick(d, "value")),
        "pnl_usd": _to_float(_pick(d, "pnl_usd")),
        "pnl_pct": _to_float(_pick(d, "pnl_pct")),
        "lev": _pick(d, "lev") if _pick(d, "lev") is not None else None,
        "liq": _pick(d, "liq") if _pick(d, "liq") is not None else None,
        "travel": _pick(d, "travel"),
    }


# --------------------- Asset icons (match Prices) ---------------------

_ASSET_ICON = {
    "BTC": ("🟡", ""),
    "ETH": ("🔷", ""),
    "SOL": ("🟣", ""),
}

def _asset_cell(symbol: str) -> Text:
    sym = (symbol or "-").upper()
    icon, _ = _ASSET_ICON.get(sym, ("•", ""))
    return Text.assemble(Text(icon + " "), Text(sym, style="bold"))


# --------------------- DataLocker readers ---------------------

def _read_positions(dl: Any) -> Tuple[List[Any], str]:
    """
    Preferred order:
      1) dl.read_positions()
      2) dl.positions.get_all_positions()
      3) DB fallback (positions table)
    """
    if dl is None:
        return [], "dl=None"

    rp = getattr(dl, "read_positions", None)
    if callable(rp):
        try:
            rows = rp() or []
            if isinstance(rows, list) and rows:
                return rows, "dl.read_positions()"
        except Exception:
            pass

    mgr = getattr(dl, "positions", None)
    gap = getattr(mgr, "get_all_positions", None) if mgr is not None else None
    if callable(gap):
        try:
            rows = gap() or []
            if isinstance(rows, list) and rows:
                return rows, "dl.positions.get_all_positions()"
        except Exception:
            pass

    try:
        db = getattr(dl, "db", None)
        if db and hasattr(db, "get_cursor"):
            cur = db.get_cursor()
            cur.execute(
                """
                SELECT *
                FROM positions
                WHERE status IN ('ACTIVE','active','OPEN','open') OR status IS NULL
                ORDER BY COALESCE(last_updated, updated_at, created_at) DESC
                LIMIT 200
                """
            )
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            if rows:
                return rows, "db:positions"
    except Exception:
        pass

    return [], "source=none"


# --------------------- Sequencer entrypoint ---------------------

def render(dl: Any, csum: Any, default_json_path: Optional[str] = None) -> None:
    """
    Sequencer entrypoint — identical signature to price_panel.
    Value column shows SIZE (abbrev). Totals row with distinct color styling.
    Lev/Liq/Travel totals are size-weighted averages; PnL is summed with sign color.
    """
    console = Console()

    # Read rows first
    rows_raw, source = _read_positions(dl)

    # Build table (borderless like Prices)
    table = Table(
        show_header=True,
        header_style="bold",
        show_lines=False,
        box=None,
        pad_edge=False,
    )
    # Columns: Asset, Side, Value(SIZE), PnL, Lev, Liq, Travel
    table.add_column("Asset", justify="left", no_wrap=True)
    table.add_column("Side", justify="left", no_wrap=True)
    table.add_column("Value", justify="right", no_wrap=True)   # shows SIZE abbreviations
    table.add_column("PnL", justify="right", no_wrap=True)
    table.add_column("Lev", justify="right", no_wrap=True)
    table.add_column("Liq", justify="right", no_wrap=True)
    table.add_column("Travel", justify="right", no_wrap=True)

    # Totals accumulators (weight by size; if missing, fallback to USD value)
    total_size = 0.0
    total_pnl = 0.0
    w_sum = 0.0
    w_lev = 0.0
    w_liq = 0.0
    w_travel = 0.0

    normalized_rows: List[Dict[str, Any]] = []
    for obj in rows_raw:
        normalized_rows.append(_normalize_row_any(obj))

    if not normalized_rows:
        table.add_row("-", "-", "-", "-", "-", "-", "-")
    else:
        for n in normalized_rows:
            size = _to_float(n.get("size"))
            usd_value = _to_float(n.get("usd_value"))
            pnl = _to_float(n.get("pnl_usd"))
            lev = _to_float(n.get("lev"))
            liq = _to_float(n.get("liq"))
            travel = _to_float(n.get("travel"))

            # choose weight: prefer absolute size, else abs(usd_value)
            weight = abs(size) if (size is not None) else (abs(usd_value) if usd_value is not None else None)

            # accumulate totals
            if size is not None:
                total_size += size
            if pnl is not None:
                total_pnl += pnl
            if weight is not None:
                w_sum += weight
                if lev is not None:
                    w_lev += lev * weight
                if liq is not None:
                    w_liq += liq * weight
                if travel is not None:
                    w_travel += travel * weight

            side_style = "green" if n["side"] == "long" else ("red" if n["side"] == "short" else "")
            table.add_row(
                _asset_cell(n["asset"]),
                Text(n["side"].capitalize() if n["side"] != "-" else "-", style=side_style),
                _abbr_count(size),  # Value column now shows SIZE
                _fmt_pnl(pnl, n.get("pnl_pct")),
                f"{lev:.2f}" if lev is not None else "-",
                f"{liq:.2f}" if liq is not None else "-",
                _percent_text(travel) if travel is not None else "-",
            )

        # --- Totals row (distinct color for non-PnL cells) ---
        lev_avg = (w_lev / w_sum) if w_sum > 0 else None
        liq_avg = (w_liq / w_sum) if w_sum > 0 else None
        travel_avg = (w_travel / w_sum) if w_sum > 0 else None

        totals_style = "bold cyan"
        pnl_total_text = _fmt_pnl(total_pnl, None) if total_pnl or total_pnl == 0 else Text("-")

        table.add_row(
            Text(""),  # Asset blank
            Text(""),  # Side blank
            Text(_abbr_count(total_size), style=totals_style),      # total size
            pnl_total_text,                                         # total pnl (red/green)
            Text(f"{lev_avg:.2f}" if lev_avg is not None else "-", style=totals_style),
            Text(f"{liq_avg:.2f}" if liq_avg is not None else "-", style=totals_style),
            Text(_percent_text(travel_avg) if travel_avg is not None else "-", style=totals_style),
        )

    # --- Title & rule (exact width match to table) ---
    console.print(Text.assemble(Text("💰 "), Text("Positions", style="bold cyan")))
    meas: Measurement = Measurement.get(console, console.options, table)
    rule = Text("─" * max(0, int(meas.maximum)), style="cyan")
    console.print(rule)

    # Provenance line and the table
    console.print(f"[POSITIONS] source: {source} ({len(rows_raw)} row{'s' if len(rows_raw)!=1 else ''})")
    console.print(table)


# Back-compat
panel = render

if __name__ == "__main__":
    render(None, {})
