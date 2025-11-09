from __future__ import annotations
"""
positions_panel.py
Sonic Reporting — Positions panel (Perps + Raydium NFTs).

UI updates:
- Extra solid rule above the title
- Title rail with only the word 'Positions' in cyan (no '(ALL)')
- Single blank line at end for padding
- Asset row icons: BTC=🟡, ETH=🔷, SOL=🟣
- Remove provenance/debug line

Totals behavior unchanged:
- Value / PnL include NFTs
- Lev/Travel are size-weighted over perps only
"""

import math
from typing import Any, Dict, List, Optional, Tuple

from .theming import (
    console_width as _theme_width,
    hr as _theme_hr,
    title_lines as _theme_title,
    want_outer_hr,
    get_panel_body_config,
    color_if_plain,
    paint_line,
)

PANEL_KEY = "positions_panel"
PANEL_NAME = "Positions"
PANEL_SLUG = "positions"

def _console_width(default: int = 92) -> int:
    return _theme_width(default)

def _hr(width: Optional[int] = None, ch: str = "─") -> str:
    return _theme_hr(width, ch)

def _right(text: str, width: int) -> str:
    return (text or "").rjust(width)

def _left(text: str, width: int) -> str:
    return (text or "").ljust(width)

# ── number/format helpers ───────────────────────────────────────────────────────
def _fmt_num(x: Any, places: int = 2, dash: str = "—") -> str:
    try:
        f = float(x)
        if math.isnan(f) or math.isinf(f):
            return dash
        if places == 0:
            return f"{int(round(f)):,}"
        if abs(f) >= 1:
            return f"{f:,.2f}"
        return f"{f:,.{places}f}"
    except Exception:
        return dash

def _fmt_usd(x: Any) -> str:
    s = _fmt_num(x, places=2, dash="—")
    return "—" if s == "—" else f"${s}"

def _fmt_pct(x: Any) -> str:
    try:
        return f"{float(x):.0f}%"
    except Exception:
        return "—"

# ── normalization (perps + nfts) ───────────────────────────────────────────────
def _norm_perp_row(rec: Dict[str, Any]) -> Dict[str, Any]:
    asset = (rec.get("asset_type") or rec.get("asset") or rec.get("symbol")
             or rec.get("pair") or rec.get("base") or "").upper()
    side = rec.get("side") or rec.get("position_type") or rec.get("direction") or ""
    size = rec.get("size") or rec.get("qty") or rec.get("amount") or 0.0
    value = (rec.get("value") or rec.get("size_usd") or rec.get("value_usd")
             or rec.get("usd_value") or rec.get("usd") or 0.0)
    pnl = rec.get("pnl") or rec.get("pnl_after_fees_usd") or rec.get("delta_usd") or 0.0
    lev = rec.get("lev") or rec.get("leverage") or rec.get("lev_x") or rec.get("x")
    liq = rec.get("liq") or rec.get("liquidation_price") or rec.get("liq_usd")
    heat = rec.get("heat") or rec.get("current_heat_index") or rec.get("heat_index")
    travel = rec.get("travel") or rec.get("travel_percent") or rec.get("move_pct")

    def _f(v, d=0.0):
        try: return float(v)
        except Exception: return d

    def _optf(v):
        try:
            return float(v) if v not in (None, "", "-") else None
        except Exception:
            return None

    return {
        "origin": "perp",
        "asset": asset,
        "side": side,
        "size": _f(size),
        "value": _f(value),
        "pnl": _f(pnl),
        "lev": _optf(lev),
        "liq": _optf(liq),
        "heat": _optf(heat),
        "travel": _optf(travel),
    }

def _norm_nft_row(nft: Dict[str, Any], pnl_usd: float) -> Dict[str, Any]:
    mint = (nft.get("mint") or "").strip()
    tag = (mint[:3].lower() if mint else "nft")
    asset_label = f"NFT-{tag}"
    try:
        value = float(nft.get("usd_total") or nft.get("usd_value") or nft.get("value_usd") or nft.get("usd") or 0.0)
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
        "size": 0.0,
        "value": value,
        "pnl": pnl,
        "lev": None, "liq": None, "heat": None, "travel": None,
        "mint": mint,
    }

# ── data collection (perps + nfts) — same as before, omitted here for brevity ──
# Keep your existing _collect_perp_rows and _collect_nft_rows implementations.
# (No behavior change needed; we only tweak rendering/UI.)

# BEGIN (unchanged) _collect_perp_rows / _collect_nft_rows
def _collect_perp_rows(ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    for key in ("positions", "perps", "perp_positions"):
        arr = ctx.get(key)
        if isinstance(arr, list) and arr:
            return [_norm_perp_row(r or {}) for r in arr], f"ctx.{key}"
    dl = ctx.get("dl")
    svc = getattr(dl, "positions", None) if dl else None
    if svc:
        for name in ("get_active_positions", "get_all_positions"):
            fn = getattr(svc, name, None)
            if callable(fn):
                try:
                    res = fn()
                    arr = (res.get("records") if isinstance(res, dict) else res) or []
                    if isinstance(arr, list) and arr:
                        rows = [_norm_perp_row(r if isinstance(r, dict) else r.__dict__) for r in arr]
                        return rows, f"dl.positions.{name}()"
                except Exception:
                    pass
    if dl:
        for prov in (getattr(dl, "perps", None), getattr(dl, "jupiter", None), getattr(dl, "positions", None)):
            if not prov: continue
            for name in ("get_open_positions","get_positions","list_positions","positions"):
                fn = getattr(prov, name, None)
                if callable(fn):
                    try:
                        res = fn()
                        arr = (res.get("records") if isinstance(res, dict) else res) or []
                        if isinstance(arr, list) and arr:
                            return [_norm_perp_row(r or {}) for r in arr], f"dl.{prov.__class__.__name__}.{name}()"
                    except Exception:
                        pass
    cursor = None
    try: cursor = ctx.get("dl").db.get_cursor() if ctx.get("dl") else None
    except Exception: cursor = None
    if cursor:
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall() or []}
        except Exception:
            tables = set()
        table = next((t for t in ("positions","dl_positions","open_positions","sonic_positions") if t in tables), None)
        if table:
            try:
                cursor.execute(f"PRAGMA table_info('{table}')")
                cols = {row[1] for row in cursor.fetchall() or []}
                if "status" in cols:
                    cursor.execute(f"SELECT * FROM {table} WHERE status IN ('ACTIVE','OPEN')")
                else:
                    cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall() or []
                if rows:
                    return [_norm_perp_row(dict(r)) for r in rows], f"sqlite:{table}"
            except Exception:
                pass
    return [], "none"

def _collect_nft_rows(ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    include = ctx.get("include_raydium_nfts", True)
    if not include: return [], "disabled"
    owner = ctx.get("owner"); dl = ctx.get("dl")
    provider = getattr(dl, "raydium", None) if dl else None
    if provider:
        try:
            fn = (getattr(provider, "get_positions", None) or
                  getattr(provider, "list_positions", None) or
                  getattr(provider, "list_lp_nfts", None) or
                  getattr(provider, "get_latest_lp_positions", None))
            curr = (fn(owner=owner) if (fn and owner is not None) else (fn() if fn else [])) or []
            curr = (curr.get("records") if isinstance(curr, dict) else curr) or []
            rows: List[Dict[str, Any]] = []
            for item in curr:
                mint = (item or {}).get("mint")
                latest = (item or {}).get("usd_total") or (item or {}).get("usd_value") or 0.0
                prev = None; hist = None
                hname = (getattr(provider, "history_for", None) or
                         getattr(provider, "get_history", None) or
                         getattr(provider, "nft_history", None))
                if callable(hname) and mint:
                    try: hist = hname(mint, limit=2)
                    except Exception: hist = None
                if isinstance(hist, list) and len(hist) >= 2:
                    try: prev = (hist[-2].get("usd_total") or hist[-2].get("usd_value") or 0.0)
                    except Exception: prev = None
                pnl = float(latest or 0.0) - float(prev or latest or 0.0)
                rows.append(_norm_nft_row(item or {}, pnl))
            return rows, "dl.raydium"
        except Exception:
            pass
    return [], "none"
# END unchanged collectors

# ── rendering ───────────────────────────────────────────────────────────────────
def render(context: Optional[Dict[str, Any]] = None, *args, **kwargs) -> List[str]:
    ctx: Dict[str, Any] = {}
    if context:
        if isinstance(context, dict): ctx.update(context)
        else: ctx["dl"] = context
    if len(args) >= 1:
        a0 = args[0];  ctx.update(a0) if isinstance(a0, dict) else ctx.setdefault("dl", a0)
    if len(args) >= 2:
        a1 = args[1]
        if isinstance(a1, dict): ctx.update(a1)
        elif isinstance(a1, (int, float)): kwargs.setdefault("width", int(a1))
    if kwargs: ctx.update(kwargs)

    width = ctx.get("width") or _console_width()

    out: List[str] = []
    W = width or _theme_width()
    wrap = want_outer_hr(PANEL_SLUG, default_string=PANEL_NAME)
    if wrap:
        out.append(_hr(W))
    out.extend(_theme_title(PANEL_SLUG, PANEL_NAME, width=W))
    if wrap:
        out.append(_hr(W))

    # Columns (unchanged layout)
    c_asset = 12; c_size = 9; c_val = 11; c_pnl = 11; c_lev = 7; c_liq = 8; c_heat = 6; c_trav = 7

    def fmt_row(asset, size, val, pnl, lev, liq, heat, trav) -> str:
        return (
            f"{_left(asset, c_asset)}  "
            f"{_right(size, c_size)}  "
            f"{_right(val, c_val)}  "
            f"{_right(pnl, c_pnl)}  "
            f"{_right(lev, c_lev)}  "
            f"{_right(liq, c_liq)}  "
            f"{_right(heat, c_heat)}  "
            f"{_right(trav, c_trav)}"
        )[:width]

    body_cfg = get_panel_body_config(PANEL_SLUG)
    header = fmt_row("🪙Asset", "📦Size", "🟩Value", "📈PnL", "🧷Lev", "💧Liq", "🔥Heat", "🧭Trave")
    out.append(paint_line(header, body_cfg["column_header_text_color"]))

    # Gather rows
    perp_rows, _ = _collect_perp_rows(ctx)
    nft_rows, _ = _collect_nft_rows(ctx)

    # Iconize asset (BTC/ETH/SOL only; leave NFT rows as-is)
    def _sym_with_icon(asset_text: str) -> str:
        s = (asset_text or "").upper()
        if s.startswith("NFT"): return asset_text
        if s == "BTC": return f"🟡 {s}"
        if s == "ETH": return f"🔷 {s}"
        if s == "SOL": return f"🟣 {s}"
        return asset_text

    # Totals
    size_sum = value_sum = pnl_sum = 0.0
    lev_weighted = travel_weighted = size_weight = 0.0

    def emit_row(row: Dict[str, Any]) -> None:
        nonlocal size_sum, value_sum, pnl_sum, lev_weighted, travel_weighted, size_weight
        asset = _sym_with_icon(row.get("asset") or "")
        size = float(row.get("size") or 0.0)
        value = float(row.get("value") or 0.0)
        pnl = float(row.get("pnl") or 0.0)
        lev = row.get("lev"); liq = row.get("liq"); heat = row.get("heat"); trav = row.get("travel")

        value_sum += value; pnl_sum += pnl
        if row.get("origin") != "nft":
            size_sum += size
            if isinstance(lev, (int, float)):   lev_weighted += size * float(lev)
            if isinstance(trav, (int, float)):  travel_weighted += size * float(trav)
            size_weight += size

        s_size = _fmt_num(size, places=2, dash="—")
        s_val  = _fmt_usd(value)
        s_pnl  = ("-" if pnl < 0 else "") + _fmt_usd(abs(pnl))
        s_lev  = f"{lev:.1f}x" if isinstance(lev, (int, float)) else "—"
        s_liq  = _fmt_usd(liq) if isinstance(liq, (int, float)) else "—"
        s_heat = _fmt_pct(heat) if isinstance(heat, (int, float)) else "—"
        s_trav = _fmt_pct(trav) if isinstance(trav, (int, float)) else "—"

        line = fmt_row(asset, s_size, s_val, s_pnl, s_lev, s_liq, s_heat, s_trav)
        out.append(color_if_plain(line, body_cfg["body_text_color"]))

    for r in perp_rows: emit_row(r)
    for r in nft_rows:  emit_row(r)

    # Totals row
    out.append("")
    tot_lev = (lev_weighted / size_weight) if size_weight > 0 else None
    tot_trv = (travel_weighted / size_weight) if size_weight > 0 else None
    s_tsize = _fmt_num(size_sum, places=2, dash="—")
    s_tval  = _fmt_usd(value_sum)
    s_tpnl  = ("-" if pnl_sum < 0 else "") + _fmt_usd(abs(pnl_sum))
    s_tlev  = f"{tot_lev:.1f}x" if isinstance(tot_lev, (int, float)) else "—"
    s_tliq  = "—"; s_theat = "—"
    s_ttrv  = f"{tot_trv:.0f}%" if isinstance(tot_trv, (int, float)) else "—"

    totals_line = fmt_row("Totals", s_tsize, s_tval, s_tpnl, s_tlev, s_tliq, s_theat, s_ttrv)
    out.append(paint_line(totals_line, body_cfg["totals_row_color"]))

    # Single trailing blank line for padding (no provenance/debug)
    out.append("")
    return out

def connector(*args, **kwargs) -> List[str]:
    return render(*args, **kwargs)

def name() -> str:
    return PANEL_NAME

if __name__ == "__main__":
    print("\n".join(render({"positions": []})))
