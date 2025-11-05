# positions_panel.py — FULL REPLACEMENT
# Borderless table; title matches Prices: "💰 Positions" + cyan rule sized to table width.
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
    "value":  ["value", "usd_value", "value_usd", "notional_usd", "notional", "size_usd", "position_value"],
    "pnl_usd":["pnl_after_fees_usd", "pnl_usd", "unrealized_pnl", "u_pnl", "profit_usd"],
    "pnl_pct":["pnl_pct", "unrealized_pnl_pct", "roe", "return_pct", "pnl_percent"],
    "lev":    ["leverage", "lev", "leverage_x"],
    "liq":    ["liquidation_price", "liq_price", "liq"],
    "travel": ["travel_percent", "travel_pct", "travel", "move_pct", "change_pct"],
}


def _normalize_row_any(obj: Any) -> Dict[str, Any]:
    d = _to_dictish(obj)

    def pick(name: str) -> Any:
        k = _find_key(d, CANDIDATES[name])
        return d[k] if k is not None else None

    raw_side = str(pick("side") or "-").lower()
    if raw_side not in ("long", "short", "-"):
        if raw_side.startswith("l"): raw_side = "long"
        elif raw_side.startswith("s"): raw_side = "short"

    return {
        "asset": str(pick("asset") or "-"),
        "side": raw_side,
        "value": _to_float(pick("value")),
        "pnl_usd": _to_float(pick("pnl_usd")),
        "pnl_pct": _to_float(pick("pnl_pct")),
        "lev": pick("lev") if pick("lev") is not None else "-",
        "liq": pick("liq") if pick("liq") is not None else "-",
        "travel": pick("travel"),
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

    # 1) convenience
    rp = getattr(dl, "read_positions", None)
    if callable(rp):
        try:
            rows = rp() or []
            if isinstance(rows, list) and rows:
                return rows, "dl.read_positions()"
        except Exception:
            pass

    # 2) manager
    mgr = getattr(dl, "positions", None)
    gap = getattr(mgr, "get_all_positions", None) if mgr is not None else None
    if callable(gap):
        try:
            rows = gap() or []
            if isinstance(rows, list) and rows:
                return rows, "dl.positions.get_all_positions()"
        except Exception:
            pass

    # 3) DB fallback
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
    Renders a borderless table that matches Prices, including a cyan rule
    under the title sized to the table width.
    """
    console = Console()

    # Build the table first so we can measure width for a matching cyan rule.
    rows_raw, source = _read_positions(dl)

    table = Table(
        show_header=True,
        header_style="bold",
        show_lines=False,
        box=None,      # borderless like Prices
        pad_edge=False,
    )
    for col, j in (("Asset","left"), ("Side","left"), ("Value","right"),
                   ("PnL","right"), ("Lev","right"), ("Liq","right"), ("Travel","right")):
        table.add_column(col, justify=j, no_wrap=True)

    if not rows_raw:
        table.add_row("-", "-", "-", "-", "-", "-", "-")
    else:
        for obj in rows_raw:
            n = _normalize_row_any(obj)
            side_style = "green" if n["side"] == "long" else ("red" if n["side"] == "short" else "")
            table.add_row(
                _asset_cell(n["asset"]),
                Text(n["side"].capitalize() if n["side"] != "-" else "-", style=side_style),
                _abbr_usd(n["value"]),
                _fmt_pnl(n["pnl_usd"], n["pnl_pct"]),
                str(n["lev"]) if n["lev"] is not None else "-",
                str(n["liq"]) if n["liq"] is not None else "-",
                _percent_text(n["travel"]) if n["travel"] is not None else "-",
            )

    # --- Title (exactly sized rule) ---
    console.print(Text.assemble(Text("💰 "), Text("Positions", style="bold cyan")))
    # Measure table width to draw a cyan rule of the same width
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
