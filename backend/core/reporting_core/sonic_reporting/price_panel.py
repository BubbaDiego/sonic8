# backend/core/reporting_core/sonic_reporting/panels/price_panel.py
from __future__ import annotations

from typing import Any, Mapping, Iterable, Optional
from datetime import datetime
import math

ASSETS = ("BTC", "ETH", "SOL")
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
        # strip leading currency symbol if present
        if s.startswith("$"):
            s = s[1:]
        try:
            return float(s)
        except Exception:
            return None
    return None


def _compact_num(x: Optional[float]) -> str:
    if x is None:
        return "—"
    a = abs(x)
    if a >= 1000:
        # match your style: 3.7k
        return f"{x/1000:.1f}k"
    if a >= 100:
        return f"{x:.0f}"
    return f"{x:.2f}"


def _fmt_delta(cur: Optional[float], prev: Optional[float]) -> tuple[str, str]:
    if cur is None or prev is None:
        return "—", "—"
    d = cur - prev
    dpct = (d / prev * 100.0) if prev != 0 else math.inf
    # sign-aware formatting
    dd = f"{d:+.2f}" if abs(d) < 1000 else f"{d/1000:+.1f}k"
    if abs(dpct) == math.inf:
        return dd, "∞%"
    return dd, f"{dpct:+.2f}%"


def _find_dict_with_assets(d: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """Return a dict that has BTC/ETH/SOL keys (any shape under those keys)."""
    if not isinstance(d, Mapping):
        return None
    if all(k in d for k in ASSETS):
        return d
    # breadth-ish search 1 level down
    for v in d.values():
        if isinstance(v, Mapping) and all(k in v for k in ASSETS):
            return v
    return None


def _extract_from_price_map(m: Mapping[str, Any]) -> dict[str, dict]:
    """
    Accept many shapes:
      {'BTC': 110234.0, 'ETH': 3920.3, 'SOL': 184.8}
      {'BTC': {'current': 110234, 'previous': 110100, 'ts': '...'}, ...}
      {'BTC': {'price': 110234, 'prev': 110100}, ...}
    """
    out: dict[str, dict] = {}
    for a in ASSETS:
        v = m.get(a)
        cur = prev = None
        ts = None
        if v is None:
            out[a] = {"current": None, "previous": None, "checked": None}
            continue
        if isinstance(v, Mapping):
            cur = _to_float(v.get("current") or v.get("price") or v.get("value") or v.get("last"))
            prev = _to_float(v.get("previous") or v.get("prev") or v.get("prior"))
            ts = v.get("ts") or v.get("checked") or v.get("updated_at") or v.get("timestamp")
        else:
            cur = _to_float(v)
        out[a] = {"current": cur, "previous": prev, "checked": ts}
    return out


def _first_nonempty(*candidates: Iterable[Optional[str]]) -> str:
    for c in candidates:
        if c:
            return str(c)
    return "—"


# ---------- extraction ----------

def _extract_prices(dl: Any, csum: Optional[Mapping[str, Any]]) -> tuple[dict[str, dict], str]:
    """
    Returns (rows, source)
      rows: {'BTC': {'current': float|None, 'previous': float|None, 'checked': Any}, ...}
      source: string used for a single breadcrumb line
    """
    # 1) Try summary directly
    if isinstance(csum, Mapping):
        # common top-level keys
        for k in ("prices", "price", "prices_state", "prices_current", "current_prices"):
            v = csum.get(k)
            if isinstance(v, Mapping):
                d = _find_dict_with_assets(v) or v
                rows = _extract_from_price_map(d)
                if any(rows[a]["current"] is not None for a in ASSETS):
                    return rows, f"csum.{k}"

        # dive one level down for {'price_monitor': {'prices': {...}}} etc.
        for k, v in csum.items():
            if isinstance(v, Mapping):
                d = _find_dict_with_assets(v) or _find_dict_with_assets(v.get("prices", {})) if isinstance(v.get("prices", {}), Mapping) else None
                if d:
                    rows = _extract_from_price_map(d)
                    if any(rows[a]["current"] is not None for a in ASSETS):
                        return rows, f"csum.{k}"

    # 2) Try DataLocker system vars (most monitor pipelines stash these)
    sys = getattr(dl, "system", None)
    if sys is not None:
        for key in ("current_prices", "prices", "last_prices", "price_cache", "prices_state"):
            try:
                cand = sys.get_var(key)
            except Exception:
                cand = None
            if isinstance(cand, Mapping):
                d = _find_dict_with_assets(cand)
                if d:
                    rows = _extract_from_price_map(d)
                    if any(rows[a]["current"] is not None for a in ASSETS):
                        return rows, f"dl.system[{key}]"

    # 3) Try common caches/holders on DataLocker
    for attr in ("prices", "cache", "portfolio"):
        holder = getattr(dl, attr, None)
        if holder and isinstance(holder, object):
            for name in ("prices", "last_prices", "current_prices", "state", "snapshot"):
                v = getattr(holder, name, None)
                if isinstance(v, Mapping):
                    d = _find_dict_with_assets(v) or v
                    rows = _extract_from_price_map(d)
                    if any(rows[a]["current"] is not None for a in ASSETS):
                        return rows, f"dl.{attr}.{name}"

    # Nothing reliable
    rows = {a: {"current": None, "previous": None, "checked": None} for a in ASSETS}
    return rows, "none"


# ---------- public render ----------

def render(*, dl: Any, csum: Optional[Mapping[str, Any]] = None) -> None:
    rows, src = _extract_prices(dl, csum)

    print("\n 💰 Prices\n")
    print(" Asset       Current   Previous   Δ   Δ%   Checked\n")
    for a in ASSETS:
        cur = rows[a]["current"]
        prev = rows[a]["previous"]
        chk = _first_nonempty(rows[a]["checked"])
        d, dp = _fmt_delta(cur, prev)
        print(
            f" {ASSET_ICON[a]} {a:<3}  "
            f"{_compact_num(cur):>8}  "
            f"{_compact_num(prev):>9}  "
            f"{d:>3}  {dp:>4}   {f'({chk})' if chk else '(—)'}"
        )
    # breadcrumb (quiet, one line)
    print(f"\n[PRICE] source: {src}")
