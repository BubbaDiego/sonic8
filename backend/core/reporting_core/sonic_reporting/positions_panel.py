# backend/core/reporting_core/sonic_reporting/panels/positions_panel.py
from __future__ import annotations

from typing import Any, Mapping, Optional, Iterable
import re

ASSET_ICON = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}


# ---------- small utils ----------

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip().replace(",", "")
        s = re.sub(r"^\$", "", s)
        s = re.sub(r"[^\d\.\-\+eE]", "", s)
        try:
            return float(s)
        except Exception:
            return None
    return None


def _fmt_money(x: Optional[float]) -> str:
    if x is None:
        return "$0.00"
    sign = "-" if x < 0 else ""
    ax = abs(x)
    return f"{sign}${ax:,.2f}"


def _fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "—"
    return f"{x:+.2f}%"


def _sym_of(r: Mapping[str, Any]) -> Optional[str]:
    for k in ("asset", "symbol", "coin", "ticker"):
        v = r.get(k)
        if isinstance(v, str) and v:
            return v.strip().upper()
    return None


def _side_of(r: Mapping[str, Any]) -> Optional[str]:
    v = r.get("side") or r.get("position_side") or r.get("pos_side")
    if isinstance(v, str) and v:
        return v.strip().upper()
    return None


def _val_of(r: Mapping[str, Any]) -> Optional[float]:
    for k in ("value", "notional", "usd_value", "size_usd"):
        v = _to_float(r.get(k))
        if v is not None:
            return v
    return None


def _pnl_of(r: Mapping[str, Any]) -> Optional[float]:
    for k in ("pnl", "pnl_usd", "profit", "pl", "p_and_l"):
        v = _to_float(r.get(k))
        if v is not None:
            return v
    return None


def _lev_of(r: Mapping[str, Any]) -> Optional[float]:
    for k in ("lev", "leverage", "x"):
        v = _to_float(r.get(k))
        if v is not None:
            return v
    return None


def _liq_of(r: Mapping[str, Any]) -> Optional[float]:
    # either direct number or "distance to liq"
    for k in ("liq", "liquidation", "liquidation_distance", "liq_dist", "liq_pct"):
        v = _to_float(r.get(k))
        if v is not None:
            return v
    risk = r.get("risk") or r.get("meta") or {}
    if isinstance(risk, Mapping):
        for k in ("liq", "liquidation", "liquidation_distance"):
            v = _to_float(risk.get(k))
            if v is not None:
                return v
    return None


def _travel_of(r: Mapping[str, Any]) -> Optional[float]:
    for k in ("travel", "move", "move_pct", "travel_pct"):
        v = _to_float(r.get(k))
        if v is not None:
            return v
    return None


def _normalize_row(r: Mapping[str, Any]) -> Optional[dict]:
    sym = _sym_of(r)
    side = _side_of(r)
    if not sym or not side:
        return None
    val = _val_of(r)
    pnl = _pnl_of(r)
    lev = _lev_of(r)
    liq = _liq_of(r)
    trv = _travel_of(r)
    return {
        "symbol": sym,
        "side": side,
        "value": val,
        "pnl": pnl,
        "lev": lev,
        "liq": liq,
        "travel": trv,
    }


# ---------- extraction ----------

def _from_iter(rows: Iterable[Any]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        if isinstance(r, Mapping):
            n = _normalize_row(r)
        else:
            n = _normalize_row(getattr(r, "__dict__", {}))
        if n:
            out.append(n)
    return out


def _extract_positions(dl: Any, csum: Optional[Mapping[str, Any]]) -> tuple[list[dict], str]:
    """
    Returns (rows, source)
    """
    # 1) csum top-level shapes
    if isinstance(csum, Mapping):
        for k in ("positions", "pos_rows", "position_rows", "portfolio_positions"):
            v = csum.get(k)
            if isinstance(v, list) and v:
                rows = _from_iter(v)
                if rows:
                    return rows, f"csum.{k}"
        # nested common
        for key, val in csum.items():
            if isinstance(val, Mapping):
                for k in ("active", "active_positions", "positions", "snapshot"):
                    v = val.get(k)
                    if isinstance(v, list) and v:
                        rows = _from_iter(v)
                        if rows:
                            return rows, f"csum.{key}.{k}"

    # 2) DataLocker common locations
    for attr in ("portfolio", "positions", "cache"):
        holder = getattr(dl, attr, None)
        if holder:
            for k in ("active", "active_positions", "positions", "last_positions", "snapshot"):
                v = getattr(holder, k, None)
                if isinstance(v, list) and v:
                    rows = _from_iter(v)
                    if rows:
                        return rows, f"dl.{attr}.{k}"
                # callable
                meth = getattr(holder, k, None)
                if callable(meth):
                    try:
                        vv = meth()
                    except Exception:
                        vv = None
                    if isinstance(vv, list) and vv:
                        rows = _from_iter(vv)
                        if rows:
                            return rows, f"dl.{attr}.{k}()"

    # 3) system var (fallbacks)
    sys = getattr(dl, "system", None)
    if sys is not None:
        for key in ("active_positions", "last_positions", "positions_snapshot"):
            try:
                vv = sys.get_var(key)
            except Exception:
                vv = None
            if isinstance(vv, list) and vv:
                rows = _from_iter(vv)
                if rows:
                    return rows, f"dl.system[{key}]"

    return [], "none"


# ---------- public render ----------

def render(*, dl: Any, csum: Optional[Mapping[str, Any]] = None) -> None:
    rows, src = _extract_positions(dl, csum)

    print("\n  ---------------------- 📈  Positions  ----------------------")
    print(" Asset   Side        Value        PnL     Lev      Liq   Travel")

    total_value = 0.0
    total_pnl = 0.0

    if not rows:
        # placeholder row
        print(" -      -             -           -       -        -        -")
    else:
        for r in rows:
            sym = r["symbol"]
            side = r["side"]
            val = r["value"]
            pnl = r["pnl"]
            lev = r["lev"]
            liq = r["liq"]
            trv = r["travel"]

            if val is not None:
                total_value += val
            if pnl is not None:
                total_pnl += pnl

            icon = ASSET_ICON.get(sym, "•")
            print(
                f" {icon} {sym:<3}  {side:<5}  "
                f"{_fmt_money(val):>10}  {_fmt_money(pnl):>8}  "
                f"{(f'{lev:.2f}×' if lev is not None else '-'):>6}  "
                f"{(f'{liq:.2f}' if liq is not None else '-'):>6}  "
                f"{(f'{trv:+.2f}%' if trv is not None else '-'):>6}"
            )

    # Totals line (same style you’ve been using)
    print(f"                  {_fmt_money(total_value):>10}  {_fmt_money(total_pnl):>8}       -                 -")

    # breadcrumb
    print(f"\n[POSITIONS] source: {src}")
