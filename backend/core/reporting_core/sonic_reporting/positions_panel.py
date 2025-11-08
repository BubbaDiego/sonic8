from __future__ import annotations

"""
positions_panel.py
Sonic Reporting — Positions (ALL) panel with Raydium LP NFTs mixed into the table.

Columns (match existing look):
  Asset | Size | Value | PnL | Lev | Liq | Heat | Trave

Behavior
- Perp rows render as before.
- Raydium LP NFTs are rendered as "position-like" rows with:
    Size=0, Lev/Liq/Heat/Trave=—, Value=usd_total, PnL=delta since previous snapshot.
- Totals row:
    - value_sum  = perps + nfts
    - pnl_sum    = perps + nfts
    - size_sum   = perps only
    - lev_avg    = size-weighted over perps only
    - travel_avg = size-weighted over perps only
    - liq total  = '—' (same as your prior behavior)

Input contract (ctx dict; no csum):
  loop_counter (int)        — optional
  width (int)               — optional; default from SONIC_CONSOLE_WIDTH or 92
  dl (DataLocker)           — optional; used to read perps & raydium
  positions / perps (list)  — optional; pre-fetched perp positions
  owner (str)               — optional; raydium wallet owner filter (preferred)
  include_raydium_nfts (bool) — optional; default True
  nft.pnl_mode (str)        — optional; "delta" (default) or "basis" (reserved)

Return: List[str] lines ready for printing.
"""

import os
import math
import datetime as _dt
from typing import Any, Dict, Iterable, List, Optional, Tuple


PANEL_KEY = "positions_panel"
PANEL_NAME = "Positions (ALL)"


# ────────────────────────────────────────────────────────────────────────────────
# Console helpers
# ────────────────────────────────────────────────────────────────────────────────

def _console_width(default: int = 92) -> int:
    try:
        w = int(os.environ.get("SONIC_CONSOLE_WIDTH", default))
        return max(80, min(180, w))
    except Exception:
        return default


def _hr(width: Optional[int] = None, ch: str = "─") -> str:
    W = width or _console_width()
    return ch * W


def _title_rail(title: str, width: Optional[int] = None, ch: str = "─") -> str:
    W = width or _console_width()
    t = f"  {title.strip()}  "
    fill = max(0, W - len(t))
    left = fill // 2
    right = fill - left
    return f"{ch * left}{t}{ch * right}"


def _abbr_middle(s: Any, front: int, back: int, min_len: int) -> str:
    s = ("" if s is None else str(s)).strip()
    if len(s) <= min_len or len(s) <= front + back + 3:
        return s
    return f"{s[:front]}…{s[-back:]}"


def _fmt_num(x: Any, places: int = 2, dash: str = "—") -> str:
    try:
        f = float(x)
        if math.isnan(f) or math.isinf(f):
            return dash
        if places == 0:
            return f"{int(round(f)):,}"
        if abs(f) >= 1:
            return f"{f:,.2f}"
        # smaller numbers keep more precision
        return f"{f:,.{places}f}"
    except Exception:
        return dash


def _fmt_usd(x: Any) -> str:
    s = _fmt_num(x, places=2, dash="—")
    return "—" if s == "—" else f"${s}"


def _fmt_pct(x: Any) -> str:
    try:
        f = float(x)
        return f"{f:.0f}%"
    except Exception:
        return "—"


def _right(text: str, width: int) -> str:
    return (text or "").rjust(width)


def _left(text: str, width: int) -> str:
    return (text or "").ljust(width)


def _get_dl_manager(dl: Any, key: str) -> Any:
    """Return a DataLocker manager by name, supporting various registry styles."""

    if not dl:
        return None

    direct = getattr(dl, key, None)
    if direct:
        return direct

    gm = getattr(dl, "get_manager", None)
    if callable(gm):
        try:
            mgr = gm(key)
            if mgr:
                return mgr
        except Exception:
            pass

    legacy = getattr(dl, "manager", None)
    if callable(legacy):
        try:
            mgr = legacy(key)
            if mgr:
                return mgr
        except Exception:
            pass

    mgrs = getattr(dl, "managers", None)
    if isinstance(mgrs, dict) and mgrs.get(key):
        return mgrs.get(key)

    getter = getattr(dl, "get", None)
    if callable(getter):
        try:
            mgr = getter(key)
            if mgr:
                return mgr
        except Exception:
            pass

    registry = getattr(dl, "registry", None)
    if isinstance(registry, dict):
        return registry.get(key)

    return None


def _get_sqlite_cursor(*sources: Any):
    """Return the first SQLite cursor available from provided sources."""

    for src in sources:
        if not src:
            continue

        fn = getattr(src, "get_cursor", None)
        if callable(fn):
            try:
                cur = fn()
                if cur:
                    return cur
            except Exception:
                pass

        db = getattr(src, "db", None)
        if db:
            db_fn = getattr(db, "get_cursor", None)
            if callable(db_fn):
                try:
                    cur = db_fn()
                    if cur:
                        return cur
                except Exception:
                    pass
            cursor_attr = getattr(db, "cursor", None)
            if callable(cursor_attr):
                try:
                    cur = cursor_attr()
                    if cur:
                        return cur
                except Exception:
                    pass

        cursor_attr = getattr(src, "cursor", None)
        if callable(cursor_attr):
            try:
                cur = cursor_attr()
                if cur:
                    return cur
            except Exception:
                pass

    return None


# ────────────────────────────────────────────────────────────────────────────────
# Normalization — Perps + NFTs
# ────────────────────────────────────────────────────────────────────────────────

def _norm_perp_row(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a Jupiter/Perps position-like record into the canonical shape.
    Fields are best-effort; we probe a few common aliases.
    """
    asset = (
        rec.get("asset_type")
        or rec.get("asset")
        or rec.get("symbol")
        or rec.get("pair")
        or rec.get("base")
        or ""
    ).upper()
    side = rec.get("side") or rec.get("position_type") or rec.get("direction") or ""
    size = rec.get("size") or rec.get("qty") or rec.get("amount") or 0.0
    value = (
        rec.get("value")
        or rec.get("size_usd")
        or rec.get("value_usd")
        or rec.get("usd_value")
        or rec.get("usd")
        or 0.0
    )
    pnl = rec.get("pnl") or rec.get("pnl_usd") or rec.get("pnl_after_fees_usd") or rec.get("delta_usd") or 0.0
    lev = rec.get("lev") or rec.get("leverage") or rec.get("lev_x") or rec.get("x")
    liq = rec.get("liq") or rec.get("liq_usd") or rec.get("liquidation_price") or rec.get("liquidation")
    heat = rec.get("heat") or rec.get("heat_pct") or rec.get("current_heat_index") or rec.get("heat_index")
    travel = rec.get("travel") or rec.get("travel_pct") or rec.get("travel_percent") or rec.get("move_pct")

    try:
        size = float(size or 0.0)
    except Exception:
        size = 0.0
    try:
        value = float(value or 0.0)
    except Exception:
        value = 0.0
    try:
        pnl = float(pnl or 0.0)
    except Exception:
        pnl = 0.0
    try:
        lev = float(lev) if lev not in (None, "", "-") else None
    except Exception:
        lev = None
    try:
        liq = float(liq) if liq not in (None, "", "-") else None
    except Exception:
        liq = None
    try:
        heat = float(heat) if heat not in (None, "", "-") else None
    except Exception:
        heat = None
    try:
        travel = float(travel) if travel not in (None, "", "-") else None
    except Exception:
        travel = None

    return {
        "origin": "perp",
        "asset": asset,
        "side": side,
        "size": size,
        "value": value,
        "pnl": pnl,
        "lev": lev,
        "liq": liq,
        "heat": heat,
        "travel": travel,
    }


def _norm_nft_row(nft: Dict[str, Any], pnl_usd: float) -> Dict[str, Any]:
    """Normalize a Raydium LP NFT record to the same row shape."""

    mint = (nft.get("mint") or "").strip()
    tag = (mint[:3].lower() if mint else "nft")
    asset_label = f"NFT-{tag}"

    usd_total = nft.get("usd_total") or nft.get("usd_value") or nft.get("value_usd") or nft.get("usd") or 0.0
    try:
        value = float(usd_total or 0.0)
    except Exception:
        value = 0.0

    try:
        pnl = float(pnl_usd or 0.0)
    except Exception:
        pnl = 0.0

    return {
        "origin": "nft",
        "asset": asset_label,
        "side": "NFT",
        "size": 0.0,          # never affects weighting
        "value": value,
        "pnl": pnl,
        "lev": None,
        "liq": None,
        "heat": None,
        "travel": None,
        "mint": mint,
    }


# ────────────────────────────────────────────────────────────────────────────────
# Data collection
# ────────────────────────────────────────────────────────────────────────────────

def _collect_perp_rows(ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """
    Try to assemble perp positions from (in order):
      1) ctx['positions'] or ctx['perps'] (list of dicts)
      2) DataLocker manager (positions)
      3) Legacy providers (dl.perps, dl.jupiter, ...)
      4) SQLite fallback tables
    """
    # 1) Direct
    for key in ("positions", "perps", "perp_positions"):
        arr = ctx.get(key)
        if isinstance(arr, list) and arr:
            rows = [_norm_perp_row(r or {}) for r in arr]
            return rows, f"ctx.{key}"

    dl = ctx.get("dl")
    svc = _get_dl_manager(dl, "positions")
    if svc:
        for name in (
            "get_active_positions",
            "get_all_positions",
            "active",
            "list_active",
            "list_positions",
            "get_positions",
            "all",
            "list",
        ):
            fn = getattr(svc, name, None)
            if callable(fn):
                try:
                    res = fn()
                    arr = (res.get("records") if isinstance(res, dict) else res) or []
                    if isinstance(arr, Iterable) and not isinstance(arr, (str, bytes)):
                        data = list(arr)
                    else:
                        data = []
                    if data:
                        rows = []
                        for item in data:
                            if isinstance(item, dict):
                                payload = item
                            elif hasattr(item, "model_dump"):
                                payload = item.model_dump()
                            elif hasattr(item, "dict"):
                                payload = item.dict()
                            else:
                                payload = getattr(item, "__dict__", {}) or {}
                            rows.append(_norm_perp_row(payload))
                        if rows:
                            return rows, f"dl.positions.{name}()"
                except Exception:
                    pass
        for attr in ("records", "positions", "items"):
            arr = getattr(svc, attr, None)
            if isinstance(arr, list) and arr:
                rows = []
                for item in arr:
                    if isinstance(item, dict):
                        payload = item
                    elif hasattr(item, "model_dump"):
                        payload = item.model_dump()
                    elif hasattr(item, "dict"):
                        payload = item.dict()
                    else:
                        payload = getattr(item, "__dict__", {}) or {}
                    rows.append(_norm_perp_row(payload))
                if rows:
                    return rows, f"dl.positions.{attr}"

    # 3) Legacy providers (perps/jupiter/etc)
    if dl:
        candidates = [
            getattr(dl, "perps", None),
            getattr(dl, "jupiter", None),
            getattr(dl, "positions", None) if getattr(dl, "positions", None) is not svc else None,
        ]
        for prov in candidates:
            if not prov:
                continue
            for name in (
                "get_open_positions",
                "get_positions",
                "list_positions",
                "positions",
            ):
                fn = getattr(prov, name, None)
                if callable(fn):
                    try:
                        res = fn()
                        arr = (res.get("records") if isinstance(res, dict) else res) or []
                        if isinstance(arr, list) and arr:
                            rows = [_norm_perp_row(r or {}) for r in arr]
                            return rows, f"dl.{prov.__class__.__name__}.{name}()"
                    except Exception:
                        pass
            for attr in ("records", "positions", "items"):
                arr = getattr(prov, attr, None)
                if isinstance(arr, list) and arr:
                    rows = [_norm_perp_row(r or {}) for r in arr]
                    return rows, f"dl.{prov.__class__.__name__}.{attr}"

    # 4) SQLite fallback
    cursor = _get_sqlite_cursor(dl, svc)
    if cursor:
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall() or []}
        except Exception:
            tables = set()
        table = next((t for t in ("positions", "dl_positions", "open_positions", "sonic_positions") if t in tables), None)
        if table:
            try:
                cursor.execute(f"PRAGMA table_info('{table}')")
                cols = {row[1] for row in cursor.fetchall() or []}
            except Exception:
                cols = set()
            query = f"SELECT * FROM {table}"
            if "status" in cols:
                query += " WHERE status IN ('ACTIVE','OPEN','open','active')"
            try:
                cursor.execute(query)
                rows = cursor.fetchall() or []
                if rows:
                    return [_norm_perp_row(dict(r)) for r in rows], f"sqlite:{table}"
            except Exception:
                pass

    return [], "none"


def _collect_nft_rows(ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """
    Fetch Raydium LP NFTs either from dl.raydium provider or via DLRaydiumManager.
    Compute PnL as delta of last two history points (or 0.0 if first seen).
    """
    include = ctx.get("include_raydium_nfts", True)
    if not include:
        return [], "disabled"

    owner = ctx.get("owner")  # optional wallet filter
    dl = ctx.get("dl")

    # 1) Try dl.raydium provider directly
    provider = getattr(dl, "raydium", None) if dl else None
    if provider:
        # get current positions / NFTs
        curr = None
        for name in ("get_positions", "list_positions", "list_lp_nfts", "get_latest_lp_positions"):
            fn = getattr(provider, name, None)
            if callable(fn):
                try:
                    res = fn() if owner is None else fn(owner=owner)
                    curr = (res.get("records") if isinstance(res, dict) else res) or []
                    if isinstance(curr, list):
                        break
                except Exception:
                    curr = None
        # compute pnl via provider history, if available
        rows: List[Dict[str, Any]] = []
        if isinstance(curr, list):
            for item in curr:
                mint = (item or {}).get("mint")
                latest = (item or {}).get("usd_total") or (item or {}).get("usd_value") or 0.0
                prev = None
                hist = None
                for hname in ("history_for", "get_history", "nft_history"):
                    fn = getattr(provider, hname, None)
                    if callable(fn) and mint:
                        try:
                            hist = fn(mint, limit=2)
                        except Exception:
                            hist = None
                        break
                if isinstance(hist, list) and len(hist) >= 2:
                    try:
                        prev = (hist[-2].get("usd_total") or hist[-2].get("usd_value") or 0.0)
                    except Exception:
                        prev = None
                pnl = float(latest or 0.0) - float(prev or latest or 0.0)
                rows.append(_norm_nft_row(item or {}, pnl))
            return rows, "dl.raydium"

    # 2) Fallback to DLRaydiumManager over the same DB
    #    We import lazily to avoid hard dependency when raydium isn't configured.
    mgr = None
    try:
        from backend.core.raydium_core.dl_raydium import DLRaydiumManager as _Mgr  # primary path
        mgr = _Mgr(getattr(getattr(dl, "db", None), "conn", None) if dl else None)
    except Exception:
        try:
            # alternative relative paths used in some branches
            from backend.core.raydium_core import dl_raydium as _dlr
            mgr = getattr(_dlr, "DLRaydiumManager", None)
            if callable(mgr):
                mgr = mgr(getattr(getattr(dl, "db", None), "conn", None) if dl else None)
        except Exception:
            mgr = None

    rows: List[Dict[str, Any]] = []
    if mgr:
        try:
            curr = mgr.get_positions(owner=owner) if hasattr(mgr, "get_positions") else []
        except Exception:
            curr = []
        for item in (curr or []):
            mint = (item or {}).get("mint")
            latest = (item or {}).get("usd_total") or (item or {}).get("usd_value") or 0.0
            prev = None
            hist = None
            try:
                if mint and hasattr(mgr, "history_for"):
                    hist = mgr.history_for(mint, limit=2)
            except Exception:
                hist = None
            if isinstance(hist, list) and len(hist) >= 2:
                try:
                    prev = (hist[-2].get("usd_total") or hist[-2].get("usd_value") or 0.0)
                except Exception:
                    prev = None
            pnl = float(latest or 0.0) - float(prev or latest or 0.0)
            rows.append(_norm_nft_row(item or {}, pnl))
        return rows, "DLRaydiumManager"

    return [], "none"


# ────────────────────────────────────────────────────────────────────────────────
# Rendering
# ────────────────────────────────────────────────────────────────────────────────

def render(context: Optional[Dict[str, Any]] = None, *args, **kwargs) -> List[str]:
    """
    Accepted:
      render(ctx)
      render(dl, ctx)
      render(ctx, width)
      render(ctx, positions=[...], owner="wallet...")
    """
    ctx: Dict[str, Any] = {}
    if context:
        if isinstance(context, dict):
            ctx.update(context)
        else:
            ctx["dl"] = context  # first arg might be DataLocker
    if len(args) >= 1:
        a0 = args[0]
        if isinstance(a0, dict):
            ctx.update(a0)
        else:
            ctx["dl"] = a0
    if len(args) >= 2:
        a1 = args[1]
        if isinstance(a1, dict):
            ctx.update(a1)
        elif isinstance(a1, (int, float)):
            kwargs.setdefault("width", int(a1))
    if kwargs:
        ctx.update(kwargs)

    width = ctx.get("width") or _console_width()
    out: List[str] = []
    out.append(_title_rail("Positions (ALL)", width))
    out.append(_hr(width))

    # Column layout (kept close to your screenshot)
    c_asset = 12
    c_size  = 9
    c_val   = 11
    c_pnl   = 11
    c_lev   = 7
    c_liq   = 8
    c_heat  = 6
    c_trav  = 7

    def fmt_row(asset, size, val, pnl, lev, liq, heat, trav) -> str:
        line = (
            f"{_left(asset, c_asset)}  "
            f"{_right(size, c_size)}  "
            f"{_right(val, c_val)}  "
            f"{_right(pnl, c_pnl)}  "
            f"{_right(lev, c_lev)}  "
            f"{_right(liq, c_liq)}  "
            f"{_right(heat, c_heat)}  "
            f"{_right(trav, c_trav)}"
        )
        return line[:width] if len(line) > width else line

    header = fmt_row("🪙Asset", "📦Size", "🟩Value", "📈PnL", "🧷Lev", "💧Liq", "🔥Heat", "🧭Trave")
    out.append(header)

    # Collect rows
    perp_rows, perp_source = _collect_perp_rows(ctx)
    nft_rows, nft_source = _collect_nft_rows(ctx)

    # Render rows (perps first)
    size_sum = 0.0
    value_sum = 0.0
    pnl_sum = 0.0
    lev_weighted = 0.0
    travel_weighted = 0.0
    size_weight = 0.0  # perps only

    def emit_row(row: Dict[str, Any]) -> None:
        nonlocal size_sum, value_sum, pnl_sum, lev_weighted, travel_weighted, size_weight

        asset = row.get("asset") or ""
        size = float(row.get("size") or 0.0)
        value = float(row.get("value") or 0.0)
        pnl = float(row.get("pnl") or 0.0)
        lev = row.get("lev")
        liq = row.get("liq")
        heat = row.get("heat")
        trav = row.get("travel")

        # totals
        value_sum += value
        pnl_sum += pnl
        if row.get("origin") != "nft":
            size_sum += size
            if isinstance(lev, (int, float)):
                lev_weighted += size * float(lev)
            if isinstance(trav, (int, float)):
                travel_weighted += size * float(trav)
            size_weight += size

        # strings
        s_size = _fmt_num(size, places=2, dash="—")
        s_val  = _fmt_usd(value)
        s_pnl  = ("-" if pnl < 0 else "") + _fmt_usd(abs(pnl))
        s_lev  = (f"{lev:.1f}x" if isinstance(lev, (int, float)) else "—")
        s_liq  = (_fmt_usd(liq) if isinstance(liq, (int, float)) else "—")
        s_heat = (_fmt_pct(heat) if isinstance(heat, (int, float)) else "—")
        s_trav = (_fmt_pct(trav) if isinstance(trav, (int, float)) else "—")

        out.append(fmt_row(asset, s_size, s_val, s_pnl, s_lev, s_liq, s_heat, s_trav))

    for r in perp_rows:
        emit_row(r)
    for r in nft_rows:
        emit_row(r)

    # Totals row
    out.append("")
    tot_lev = (lev_weighted / size_weight) if size_weight > 0 else None
    tot_trv = (travel_weighted / size_weight) if size_weight > 0 else None
    s_tsize = _fmt_num(size_sum, places=2, dash="—")
    s_tval  = _fmt_usd(value_sum)
    s_tpnl  = ("-" if pnl_sum < 0 else "") + _fmt_usd(abs(pnl_sum))
    s_tlev  = (f"{tot_lev:.1f}x" if isinstance(tot_lev, (int, float)) else "—")
    s_tliq  = "—"
    s_theat = "—"
    s_ttrv  = (f"{tot_trv:.0f}%" if isinstance(tot_trv, (int, float)) else "—")

    out.append(fmt_row("Totals", s_tsize, s_tval, s_tpnl, s_tlev, s_tliq, s_theat, s_ttrv))
    out.append(f"[POSITIONS] perps={perp_source}({len(perp_rows)}) nfts={nft_source}({len(nft_rows)})")
    return out


def connector(*args, **kwargs) -> List[str]:
    return render(*args, **kwargs)


def name() -> str:
    return PANEL_NAME


if __name__ == "__main__":
    # Demo: 1 perp + 1 nft
    demo_ctx = {
        "positions": [
            {"asset": "SOL", "size": 178.35, "value_usd": 167.80, "pnl_usd": -9.87, "lev": 10.1, "liq_usd": 171, "heat_pct": 6, "travel_pct": -3},
        ],
        # "dl": ...  # optional DataLocker for Raydium
    }
    for ln in render(demo_ctx):
        print(ln)
