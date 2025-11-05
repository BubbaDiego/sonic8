# -*- coding: utf-8 -*-
from __future__ import annotations
"""
positions_panel — DL-sourced positions table (adaptive)

- Adapts to multiple DataLocker shapes (get_manager / manager / managers[...] / get / registry).
- Falls back to DB if possible (get_db / db / connect_db / db attr).
- Normalizes fields so Asset/Side/value/pnl/lev/liq/travel render consistently.
- Sequencer contract: render(dl, csum, default_json_path).
"""

from typing import Any, Mapping, Optional, Dict, List, Tuple
import sqlite3

# Optional imports (don’t crash if unavailable)
try:
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:
    DataLocker = None  # type: ignore

# Reuse aligned printer if available
try:
    from backend.core.reporting_core.sonic_reporting.positions_snapshot import _print_positions_table as _print_table  # type: ignore
except Exception:
    _print_table = None  # type: ignore


# ---------- small utils ----------
def _as_dict(obj: Any) -> Mapping[str, Any]:
    if isinstance(obj, Mapping):
        return obj
    return getattr(obj, "__dict__", {}) or {}


def _get_any(row: Mapping[str, Any], *names: str) -> Any:
    for n in names:
        if n in row:
            return row.get(n)
    for nest in ("risk", "meta", "stats"):
        d = row.get(nest)
        if isinstance(d, Mapping):
            for n in names:
                if n in d:
                    return d.get(n)
    return None


def _as_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


# ---------- normalization ----------
def _normalize_row(p: Any) -> Dict[str, Any]:
    row = _as_dict(p)

    asset = _get_any(row, "asset", "symbol", "ticker", "coin", "name", "asset_type", "base_asset")
    if isinstance(asset, str):
        asset = asset.upper()
    elif asset is None:
        asset = "---"

    side = _get_any(row, "side", "position", "dir", "direction", "position_side", "long_short")
    if side is None:
        is_long = _get_any(row, "is_long", "long")
        if isinstance(is_long, bool):
            side = "LONG" if is_long else "SHORT"
    side = (str(side or "LONG")).upper()
    if side not in ("LONG", "SHORT"):
        side = "LONG"

    value = _as_float(_get_any(row, "value", "value_usd", "size_usd", "notional", "notional_usd"))
    pnl   = _as_float(_get_any(row, "pnl", "pnl_usd", "pnl_after_fees_usd", "unrealized_pnl", "profit", "pl"))
    lev   = _as_float(_get_any(row, "lev", "leverage", "x"))
    liq   = _as_float(_get_any(row, "liq", "liq_pct", "liquidation", "liquidation_distance", "liquidation_distance_pct", "liq_dist"))
    travel = _as_float(_get_any(row, "travel", "travel_pct", "move_pct", "move", "change_pct", "delta_pct"))

    # Compute travel if possible
    if travel is None:
        entry = _as_float(_get_any(row, "entry", "entry_price"))
        mark  = _as_float(_get_any(row, "mark", "mark_price", "price"))
        liq_price = _as_float(_get_any(row, "liq_price", "liquidation_price"))
        if entry and mark:
            if side == "SHORT":
                travel = (entry - mark) / entry * 100.0
                if liq_price is not None and mark >= liq_price:
                    travel = -100.0
            else:
                travel = (mark - entry) / entry * 100.0
                if liq_price is not None and mark <= liq_price:
                    travel = -100.0

    return {
        "asset": asset or "---",
        "side": side,
        "value": value,
        "pnl": pnl,
        "lev": lev,
        "liq": liq,
        "travel": travel,
    }


# ---------- DataLocker adapters ----------
def _dl_instance(passed_dl: Any = None) -> Any:
    if passed_dl:
        return passed_dl
    if DataLocker is None:
        raise RuntimeError("DataLocker module not available")
    try:
        get_inst = getattr(DataLocker, "get_instance", None)
        if callable(get_inst):
            inst = get_inst()
            if inst:
                return inst
    except Exception:
        pass
    return DataLocker()  # last resort


def _resolve_manager(dl: Any, name: str) -> Tuple[Any, str]:
    gm = getattr(dl, "get_manager", None)
    if callable(gm):
        try:
            m = gm(name)
            if m:
                return m, "dl:get_manager"
        except Exception:
            pass

    fn = getattr(dl, "manager", None)
    if callable(fn):
        try:
            m = fn(name)
            if m:
                return m, "dl:manager()"
        except Exception:
            pass

    mgrs = getattr(dl, "managers", None)
    if isinstance(mgrs, dict) and name in mgrs:
        return mgrs[name], "dl:managers[]"

    get = getattr(dl, "get", None)
    if callable(get):
        try:
            m = get(name)
            if m:
                return m, "dl:get()"
        except Exception:
            pass

    reg = getattr(dl, "registry", None)
    if isinstance(reg, dict) and name in reg:
        return reg[name], "dl:registry[]"

    return None, "dl:manager:none"


def _list_known_managers(dl: Any) -> str:
    try:
        am = getattr(dl, "available_managers", None)
        if callable(am):
            return ", ".join(sorted(am()))
    except Exception:
        pass
    keys = []
    try:
        mgrs = getattr(dl, "managers", None)
        if isinstance(mgrs, dict):
            keys.extend(list(mgrs.keys()))
    except Exception:
        pass
    try:
        reg = getattr(dl, "registry", None)
        if isinstance(reg, dict):
            keys.extend([k for k in reg.keys() if k not in keys])
    except Exception:
        pass
    return ", ".join(sorted(keys)) if keys else "—"


def _manager_rows(mgr: Any) -> Tuple[List[Mapping[str, Any]], str]:
    if mgr is None:
        return [], "mgr:none"

    for meth, tag in (
        ("active", "mgr:active()"),
        ("list_active", "mgr:list_active()"),
        ("list", "mgr:list()"),
        ("all", "mgr:all()"),
    ):
        fn = getattr(mgr, meth, None)
        if callable(fn):
            try:
                rows = fn()
                return [_as_dict(r) for r in (rows or [])], tag
            except Exception:
                pass

    rows = getattr(mgr, "rows", None)
    if isinstance(rows, (list, tuple)):
        return [_as_dict(r) for r in rows], "mgr:.rows"

    return [], "mgr:none"


def _db_conn(dl: Any) -> Optional[sqlite3.Connection]:
    for name in ("get_db", "db", "connect_db"):
        fn = getattr(dl, name, None)
        if callable(fn):
            try:
                conn = fn()
                if isinstance(conn, sqlite3.Connection):
                    return conn
            except Exception:
                continue
    db_attr = getattr(dl, "db", None)
    if isinstance(db_attr, sqlite3.Connection):
        return db_attr
    return None


def _rows_from_db(dl: Any) -> Tuple[List[Mapping[str, Any]], str]:
    conn = _db_conn(dl)
    if not conn:
        return [], "db:none"
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(positions)")
        cols = {c[1] for c in cur.fetchall()}
        order_col = "updated_at" if "updated_at" in cols else ("created_at" if "created_at" in cols else "rowid")
        cur.execute(
            f"""
            SELECT * FROM positions
            WHERE status IN ('active','OPEN','open') OR status IS NULL
            ORDER BY {order_col} DESC
            LIMIT 200
        """
        )
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()], "db:fallback"
    except Exception:
        return [], "db:error"
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------- render ----------
def _render_core(dl: Any) -> None:
    mgr, src_a = _resolve_manager(dl, "positions")
    rows_raw, src_b = _manager_rows(mgr)

    if not rows_raw:
        # helpful diagnostics when no manager was found
        if src_a == "dl:manager:none":
            known = _list_known_managers(dl)
            if known and known != "—":
                print(f"[POSITIONS] known managers: {known}")
        rows_raw, src_b = _rows_from_db(dl)

    rows = [_normalize_row(p) for p in rows_raw]

    if _print_table is not None:
        _print_table(rows)
    else:
        # simple fallback layout
        print("Asset Side        Value        PnL     Lev      Liq   Travel")
        if not rows:
            print("-     -               -          -       -        -        -")
        else:
            for r in rows:
                asset = f"{r['asset']:<5}"
                side  = f"{r['side']:<5}"
                val   = f"{(r['value'] or 0):>10,.2f}"
                pnl   = f"{(r['pnl'] or 0):>10,.2f}"
                lev   = "" if r["lev"] is None else f"{r['lev']:.2f}"
                liq   = "" if r["liq"] is None else f"{r['liq']:.2f}%"
                trav  = "" if r["travel"] is None else f"{r['travel']:.2f}%"
                print(f"{asset} {side} {val:>10} {pnl:>10} {lev:>7} {liq:>7} {trav:>7}")

        tv = sum((r["value"] or 0) for r in rows)
        tp = sum((r["pnl"] or 0) for r in rows)
        print(f"\n{'':18}${tv:,.2f}  ${tp:,.2f}       -                 -")

    print(f"\n[POSITIONS] {src_a} -> {src_b} ({len(rows)} rows)")


def print_positions_panel(dl=None) -> None:
    if dl is None:
        dl = _dl_instance()
    _render_core(dl)


def render(dl=None, csum=None, default_json_path=None, **_):
    print_positions_panel(dl=dl)
