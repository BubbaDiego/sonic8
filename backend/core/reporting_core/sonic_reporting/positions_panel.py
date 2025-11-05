# positions_panel.py — FULL REPLACEMENT (schema-agnostic with fuzzy key mapping)
# Sequencer contract: render(dl, csum, default_json_path=None)
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple
from dataclasses import is_dataclass, asdict

from rich.console import Console
from rich.table import Table
from rich.text import Text


# --------------------- Title (mirror wallet_panel style) ---------------------

def _resolve_wallet_title_fn():
    try:
        from . import wallet_panel as _wallet_panel  # type: ignore
        for name in ("render_title", "title", "section_title", "print_title", "header"):
            if hasattr(_wallet_panel, name):
                return getattr(_wallet_panel, name)
    except Exception:
        pass
    return None

_WALLET_TITLE_FN = _resolve_wallet_title_fn()

def _print_title(console: Console, title: str) -> None:
    if _WALLET_TITLE_FN:
        try:
            _WALLET_TITLE_FN(console, title)  # type: ignore
            return
        except TypeError:
            try:
                _WALLET_TITLE_FN(title)  # type: ignore
                return
            except Exception:
                pass
        except Exception:
            pass
    bullet = "•"
    console.print(Text.assemble(Text(f"{bullet} ", style="bold"),
                                Text(title, style="bold underline")))


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


# --------------------- Row materialization & fuzzy mapping ---------------------

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
    # 1) exact (case-insensitive)
    for c in candidates:
        lc = c.lower()
        if lc in lower_map:
            return lower_map[lc]
    # 2) substring fuzzy
    for c in candidates:
        lc = c.lower()
        for lk, original in lower_map.items():
            if lc in lk:
                return original
    return None

# preferred key candidates per column
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

def _normalize_row_any(obj: Any) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Normalize any object/dict into our panel row dict plus the mapping used.
    Returns (row, mapping).
    """
    d = _to_dictish(obj)
    mapping: Dict[str, str] = {}
    out: Dict[str, Any] = {}

    # asset
    k = _find_key(d, CANDIDATES["asset"])
    out["asset"] = str(d[k]) if k else "-"
    if k: mapping["asset"] = k

    # side
    k = _find_key(d, CANDIDATES["side"])
    side_val = str(d[k]).lower() if k else "-"
    if side_val not in ("long", "short", "-"):
        # normalize common variants
        if side_val.startswith("l"): side_val = "long"
        elif side_val.startswith("s"): side_val = "short"
    out["side"] = side_val
    if k: mapping["side"] = k

    # value
    k = _find_key(d, CANDIDATES["value"])
    out["value"] = _to_float(d[k]) if k else None
    if k: mapping["value"] = k

    # pnl usd
    k = _find_key(d, CANDIDATES["pnl_usd"])
    out["pnl_usd"] = _to_float(d[k]) if k else None
    if k: mapping["pnl_usd"] = k

    # pnl pct
    k = _find_key(d, CANDIDATES["pnl_pct"])
    out["pnl_pct"] = _to_float(d[k]) if k else None
    if k: mapping["pnl_pct"] = k

    # leverage
    k = _find_key(d, CANDIDATES["lev"])
    out["lev"] = d[k] if k else "-"
    if k: mapping["lev"] = k

    # liq
    k = _find_key(d, CANDIDATES["liq"])
    out["liq"] = d[k] if k else "-"
    if k: mapping["liq"] = k

    # travel
    k = _find_key(d, CANDIDATES["travel"])
    out["travel"] = d[k] if k else None
    if k: mapping["travel"] = k

    return out, mapping


# --------------------- DataLocker readers ---------------------

def _read_positions(dl: Any) -> Tuple[List[Any], str]:
    """
    Correct access preference:
      1) dl.read_positions()
      2) dl.positions.get_all_positions()
      3) DB fallback
    """
    if dl is None:
        return [], "dl=None"

    # 1) locker convenience
    rp = getattr(dl, "read_positions", None)
    if callable(rp):
        try:
            rows = rp() or []
            if isinstance(rows, list):
                if rows:
                    return rows, "dl.read_positions()"
                else:
                    # empty but valid path, keep looking
                    pass
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

    # 3) SQL fallback
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
    Sequencer entrypoint — matches price_panel signature.
    """
    console = Console()
    _print_title(console, "Positions")

    rows_raw, source = _read_positions(dl)
    console.print(f"[POSITIONS] source: {source} ({len(rows_raw)} row{'s' if len(rows_raw)!=1 else ''})")

    table = Table(show_header=True, header_style="bold")
    for col, j in (("Asset","left"), ("Side","left"), ("Value","right"),
                   ("PnL","right"), ("Lev","right"), ("Liq","right"), ("Travel","right")):
        table.add_column(col, justify=j)

    if not rows_raw:
        table.add_row("-", "-", "-", "-", "-", "-", "-")
        console.print(table)
        return

    showed_debug_keys = False
    for obj in rows_raw:
        norm, mapping = _normalize_row_any(obj)

        # If the row looks totally un-mapped, print keys once to help lock schema quickly.
        if (norm["asset"] == "-" and norm["side"] == "-" and
            norm["value"] is None and norm["pnl_usd"] is None and
            norm["pnl_pct"] is None and norm["lev"] == "-" and
            norm["liq"] == "-" and norm["travel"] is None):
            if not showed_debug_keys:
                keys = list(_to_dictish(obj).keys())
                console.print(f"[POSITIONS] debug: unmapped row keys → {keys}")
                showed_debug_keys = True

        side_style = "green" if norm["side"] == "long" else ("red" if norm["side"] == "short" else "")
        table.add_row(
            norm["asset"],
            Text(norm["side"].capitalize() if norm["side"] != "-" else "-", style=side_style),
            _abbr_usd(norm["value"]),
            _fmt_pnl(norm["pnl_usd"], norm["pnl_pct"]),
            str(norm["lev"]) if norm["lev"] is not None else "-",
            str(norm["liq"]) if norm["liq"] is not None else "-",
            _percent_text(norm["travel"]) if norm["travel"] is not None else "-",
        )

    console.print(table)


# Back-compat for any callers importing `panel`
panel = render

if __name__ == "__main__":
    render(None, {})
