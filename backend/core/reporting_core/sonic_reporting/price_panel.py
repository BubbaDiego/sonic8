from __future__ import annotations
"""
price_panel.py
Sonic Reporting — Prices panel (console)

Goals
- Match the common console style used by other panels.
- Accept a single ctx dict or (dl, ctx, width) via connector(...).
- No csum dependency.
- Be forgiving about sources:
    1) ctx['prices'] (list of dicts)
    2) dl.price / dl.prices / dl.market providers (get_prices/list_prices/get_latest_prices)
- Render even when empty (header + provenance).
"""

import os
import datetime as _dt
from typing import Any, Dict, List, Optional, Tuple


PANEL_KEY = "price_panel"
PANEL_NAME = "Prices"


# ───────────────────────────────────── helpers ─────────────────────────────────────

def _console_width(default: int = 92) -> int:
    try:
        w = int(os.environ.get("SONIC_CONSOLE_WIDTH", default))
        return max(60, min(180, w))
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

def _fmt_price(v: Any) -> str:
    try:
        x = float(v)
        if abs(x) >= 1:
            return f"${x:,.2f}"
        return f"${x:.6f}"
    except Exception:
        return "—"

def _fmt_time(ts: Any) -> str:
    try:
        if isinstance(ts, (_dt.datetime,)):
            dt = ts
        elif isinstance(ts, (int, float)):
            dt = _dt.datetime.fromtimestamp(float(ts))
        elif isinstance(ts, str):
            s = ts.strip()
            if s.endswith("Z"):
                dt = _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
            else:
                dt = _dt.datetime.fromisoformat(s)
        else:
            dt = _dt.datetime.now()
    except Exception:
        dt = _dt.datetime.now()
    h = dt.strftime("%I").lstrip("0") or "0"
    return f"{dt.strftime('%m/%d')} • {h}:{dt.strftime('%M%p').lower()}"

def _abbr_mid(s: Any, front: int = 5, back: int = 4, min_len: int = 10) -> str:
    s = ("" if s is None else str(s)).strip()
    if len(s) <= min_len or len(s) <= front + back + 3:
        return s
    return f"{s[:front]}…{s[-back:]}"


# ─────────────────────────────── data collection ───────────────────────────────

def _coalesce(*vals, default=None):
    for v in vals:
        if v not in (None, ""):
            return v
    return default

def _norm_price(rec: Dict[str, Any]) -> Dict[str, Any]:
    sym = (rec.get("symbol") or rec.get("asset") or rec.get("pair") or rec.get("base") or "").upper()
    price = _coalesce(rec.get("price"), rec.get("last"), rec.get("px"), rec.get("usd"), 0.0)
    ts = rec.get("checked_ts") or rec.get("ts") or rec.get("timestamp") or rec.get("time")
    return {"symbol": sym, "price": price, "ts": ts}

def _collect_prices(ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    # 1) direct ctx
    direct = ctx.get("prices")
    if isinstance(direct, list) and direct:
        return [_norm_price(r or {}) for r in direct], "ctx.prices"

    dl = ctx.get("dl")
    if dl:
        # 2) probable providers
        for prov in (getattr(dl, "price", None), getattr(dl, "prices", None), getattr(dl, "market", None)):
            if not prov:
                continue
            # common methods
            for name in ("get_prices", "list_prices", "get_latest_prices", "get_tickers"):
                fn = getattr(prov, name, None)
                if callable(fn):
                    try:
                        res = fn()
                        arr = (res.get("records") if isinstance(res, dict) else res) or []
                        if isinstance(arr, list) and arr:
                            return [_norm_price(r or {}) for r in arr], f"dl.{prov.__class__.__name__}.{name}()"
                    except Exception:
                        pass
            # attributes fallback
            for attr in ("records", "items", "prices", "tickers"):
                arr = getattr(prov, attr, None)
                if isinstance(arr, list) and arr:
                    return [_norm_price(r or {}) for r in arr], f"dl.{prov.__class__.__name__}.{attr}"

    return [], "none"


# ───────────────────────────────────── render ───────────────────────────────────

def render(context: Optional[Dict[str, Any]] = None, *args, **kwargs) -> List[str]:
    """
    Accepted:
      render(ctx)
      render(dl, ctx)
      render(ctx, width)
    """
    ctx: Dict[str, Any] = {}
    if context:
        if isinstance(context, dict): ctx.update(context)
        else: ctx["dl"] = context
    if len(args) >= 1:
        a0 = args[0]
        if isinstance(a0, dict): ctx.update(a0)
        else: ctx["dl"] = a0
    if len(args) >= 2:
        a1 = args[1]
        if isinstance(a1, dict): ctx.update(a1)
        elif isinstance(a1, (int, float)): kwargs.setdefault("width", int(a1))
    if kwargs: ctx.update(kwargs)

    width = ctx.get("width") or _console_width()

    out: List[str] = []
    out.append(_title_rail("Prices", width))
    out.append(_hr(width))

    # columns
    c_sym, c_px, c_ts = 12, 14, 14
    def fmt_row(sym, px, ts) -> str:
        line = f"{_abbr_mid(sym, 4, 3, c_sym):<{c_sym}}  {px:>{c_px}}  {ts:>{c_ts}}"
        return line[:width] if len(line) > width else line

    out.append(fmt_row("Asset", "Price", "Checked"))

    items, source = _collect_prices(ctx)
    if items:
        for r in items:
            out.append(fmt_row(r.get("symbol",""), _fmt_price(r.get("price")), _fmt_time(r.get("ts"))))
    else:
        out.append("(no prices)")

    out.append("")
    out.append(f"[PRICES] source={source} count={len(items)}")
    return out

def connector(*args, **kwargs) -> List[str]:
    return render(*args, **kwargs)

def name() -> str:
    return PANEL_NAME

if __name__ == "__main__":
    demo = [{"symbol": "BTC", "price": 118755.0, "checked_ts": _dt.datetime.now().isoformat(timespec="seconds")}]
    for ln in render({"prices": demo}):
        print(ln)
