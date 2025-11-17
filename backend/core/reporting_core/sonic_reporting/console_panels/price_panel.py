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

import datetime as _dt
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich import box

try:
    # Reuse a shared icon mapping when available.
    from backend.core.reporting_core.sonic_reporting.positions_icons import icon_for  # type: ignore
except Exception:  # pragma: no cover
    def icon_for(sym: str) -> str:
        mapping = {"BTC": "🟠", "ETH": "🔷", "SOL": "🟣"}
        return mapping.get((sym or "").upper(), "🪙")

# Trend helper using PriceMonitor's prices history
from backend.core.reporting_core.sonic_reporting import price_trends as _price_trends

from .theming import (
    console_width as _theme_width,
    emit_title_block,
    get_panel_body_config,
    body_pad_above,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
    paint_line,
)


PANEL_KEY = "price_panel"
PANEL_NAME = "Prices"
PANEL_SLUG = "prices"


# ───────────────────────────────────── helpers ─────────────────────────────────────

def _console_width(default: int = 92) -> int:
    return _theme_width(default)


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


def _coalesce(*vals, default=None):
    for v in vals:
        if v not in (None, ""):
            return v
    return default


def _get_dl_manager(dl: Any, key: str) -> Any:
    """Return a DataLocker manager by name, supporting multiple registry styles."""

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
    """Return the first SQLite cursor available from the provided sources."""

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


def _norm_price(rec: Dict[str, Any]) -> Dict[str, Any]:
    sym = (
        rec.get("asset_type")
        or rec.get("asset")
        or rec.get("symbol")
        or rec.get("ticker")
        or rec.get("pair")
        or rec.get("base")
        or rec.get("name")
        or ""
    ).upper()
    price = _coalesce(
        rec.get("current_price"),
        rec.get("price"),
        rec.get("last"),
        rec.get("px"),
        rec.get("usd"),
        0.0,
    )
    ts = _coalesce(
        rec.get("last_update_time"),
        rec.get("previous_update_time"),
        rec.get("checked_ts"),
        rec.get("ts"),
        rec.get("timestamp"),
        rec.get("time"),
    )
    return {"symbol": sym, "price": price, "ts": ts}


def _latest_by_symbol(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return only the newest record per symbol."""

    def _as_ts(value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                if value.endswith("Z"):
                    return _dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
                return _dt.datetime.fromisoformat(value).timestamp()
            except Exception:
                return 0.0
        if isinstance(value, _dt.datetime):
            return value.timestamp()
        return 0.0

    best: Dict[str, Dict[str, Any]] = {}
    for row in items:
        sym = (row.get("symbol") or "").upper()
        if not sym:
            continue
        ts = _as_ts(row.get("ts"))
        if sym not in best or ts >= _as_ts(best[sym].get("ts")):
            best[sym] = row
    return [best[key] for key in sorted(best.keys())]


def _collect_prices(ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    # 1) direct ctx
    direct = ctx.get("prices")
    if isinstance(direct, list) and direct:
        rows = [_norm_price(r or {}) for r in direct]
        return _latest_by_symbol(rows), "ctx.prices"

    dl = ctx.get("dl")

    # 2) DataLocker manager (preferred)
    svc = _get_dl_manager(dl, "prices")
    if svc:
        for name in (
            "get_all_prices",
            "list_prices",
            "get_prices",
            "get_latest_prices",
            "all",
            "list",
        ):
            fn = getattr(svc, name, None)
            if callable(fn):
                try:
                    res = fn()
                    arr = (res.get("records") if isinstance(res, dict) else res) or []
                    if isinstance(arr, list) and arr:
                        rows = [
                            _norm_price(r if isinstance(r, dict) else getattr(r, "__dict__", {}) or {})
                            for r in arr
                        ]
                        return _latest_by_symbol(rows), f"dl.prices.{name}()"
                except Exception:
                    pass
        for attr in ("records", "items", "prices"):
            arr = getattr(svc, attr, None)
            if isinstance(arr, list) and arr:
                rows = [
                    _norm_price(r if isinstance(r, dict) else getattr(r, "__dict__", {}) or {})
                    for r in arr
                ]
                return _latest_by_symbol(rows), f"dl.prices.{attr}"

    # 3) Legacy providers on dl
    if dl:
        for prov in (getattr(dl, "price", None), getattr(dl, "market", None)):
            if not prov:
                continue
            for name in ("get_prices", "list_prices", "get_latest_prices", "get_tickers"):
                fn = getattr(prov, name, None)
                if callable(fn):
                    try:
                        res = fn()
                        arr = (res.get("records") if isinstance(res, dict) else res) or []
                        if isinstance(arr, list) and arr:
                            rows = [_norm_price(r or {}) for r in arr]
                            return _latest_by_symbol(rows), f"dl.{prov.__class__.__name__}.{name}()"
                    except Exception:
                        pass
            for attr in ("records", "items", "prices", "tickers"):
                arr = getattr(prov, attr, None)
                if isinstance(arr, list) and arr:
                    rows = [_norm_price(r or {}) for r in arr]
                    return _latest_by_symbol(rows), f"dl.{prov.__class__.__name__}.{attr}"

    # 4) SQLite fallback
    cursor = _get_sqlite_cursor(dl, svc)
    if cursor:
        candidates = ("prices", "dl_prices", "market_prices", "sonic_prices")
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall() or []}
        except Exception:
            tables = set()
        table = next((t for t in candidates if t in tables), None)
        if table:
            try:
                cursor.execute(f"PRAGMA table_info('{table}')")
                cols = {row[1] for row in cursor.fetchall() or []}
            except Exception:
                cols = set()
            asset_col = next((c for c in ("asset_type", "asset", "symbol", "ticker", "name") if c in cols), None)
            price_col = next((c for c in ("current_price", "price", "px", "usd") if c in cols), None)
            time_col = next((c for c in ("last_update_time", "ts", "timestamp", "checked_ts", "previous_update_time") if c in cols), None)
            if asset_col and price_col and time_col:
                try:
                    cursor.execute(
                        f"SELECT {asset_col} AS asset, {price_col} AS price, {time_col} AS ts FROM {table}"
                    )
                    rows = cursor.fetchall() or []
                    if rows:
                        data = [_norm_price(dict(r)) for r in rows]
                        return _latest_by_symbol(data), f"sqlite:{table}"
                except Exception:
                    pass

    return [], "none"


# ─────────────────────────── Rich plumbing & formatting ───────────────────────

def _resolve_table_cfg(body_cfg: Dict[str, Any]) -> Dict[str, Any]:
    tcfg = (body_cfg or {}).get("table") or {}
    style = str(tcfg.get("style") or "invisible").lower().strip()
    table_justify = str(tcfg.get("table_justify") or "left").lower().strip()
    header_justify = str(tcfg.get("header_justify") or "left").lower().strip()
    return {
        "style": style,
        "table_justify": table_justify,
        "header_justify": header_justify,
    }


def _style_to_box(style: str):
    style = (style or "").lower()
    if style == "thin":
        return box.SIMPLE_HEAD, False
    if style == "thick":
        return box.HEAVY_HEAD, True
    # "invisible" or unknown → no borders
    return None, False


def _justify_lines(lines: List[str], justify: str, width: int) -> List[str]:
    justify = (justify or "left").lower()
    out: List[str] = []
    for line in lines:
        s = line.rstrip("\n")
        pad = max(0, width - len(s))
        if justify == "right":
            out.append(" " * pad + s)
        elif justify == "center":
            left = pad // 2
            out.append(" " * left + s)
        else:
            out.append(s)
    return out


def _fmt_symbol(sym: str) -> str:
    label = (sym or "").upper()
    return f"{icon_for(label)} {label}".strip()


def _fmt_trend(pct: Optional[float]) -> str:
    """
    Format a % move as an arrow + percent.

    Requirements:
      - Up arrow green, down arrow red.
      - Percent text stays uncolored for consistent alignment.
      - Tiny moves (< 0.01%) treated as flat in grey.
    """
    if pct is None:
        return "—"
    try:
        v = float(pct)
    except Exception:
        return "—"

    # Tiny moves → visually "flat"
    if abs(v) < 0.01:
        return "[grey50]0.0%[/]"

    if v > 0:
        # green arrow, plain percentage
        return f"[green]▲[/] {abs(v):.2f}%"
    else:
        # red arrow, plain percentage
        return f"[red]▼[/] {abs(v):.2f}%"


def _build_rich_table(
    rows: List[Dict[str, Any]],
    trends: Dict[str, Dict[str, Optional[float]]],
    body_cfg: Dict[str, Any],
    width: int,
) -> List[str]:
    table_cfg = _resolve_table_cfg(body_cfg)
    box_style, show_lines = _style_to_box(table_cfg["style"])

    table = Table(
        show_header=True,
        header_style="",
        show_lines=show_lines,
        box=box_style,
        pad_edge=False,
        expand=False,
    )

    # Header labels with icons to match the rest of the console
    table.add_column("🪙 Asset", justify="left", no_wrap=True)
    table.add_column("💵 Price", justify="right")
    table.add_column("🕒 Checked", justify="left")
    table.add_column("🕐 1h", justify="right", no_wrap=True)
    table.add_column("🕕 6h", justify="right", no_wrap=True)
    table.add_column("🕛 12h", justify="right", no_wrap=True)

    for r in rows:
        sym = (r.get("symbol") or "").upper()
        trend_row = (trends or {}).get(sym, {})
        table.add_row(
            _fmt_symbol(sym),
            _fmt_price(r.get("price")),
            _fmt_time(r.get("ts")),
            _fmt_trend(trend_row.get("1h")),
            _fmt_trend(trend_row.get("6h")),
            _fmt_trend(trend_row.get("12h")),
        )

    buf = StringIO()
    console = Console(record=True, width=width, file=buf, force_terminal=True)
    console.print(table)
    text = console.export_text().rstrip("\n")
    if not text:
        return []

    raw_lines = text.splitlines()
    return _justify_lines(raw_lines, table_cfg["table_justify"], width)


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
        if isinstance(context, dict):
            ctx.update(context)
        else:
            ctx["dl"] = context
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

    width = int(ctx.get("width") or _console_width())

    body_cfg = get_panel_body_config(PANEL_SLUG)
    lines: List[str] = []
    lines.extend(emit_title_block(PANEL_SLUG, PANEL_NAME))
    lines.extend(body_pad_above(PANEL_SLUG))

    items, source = _collect_prices(ctx)

    if not items:
        # Empty state → static header + message
        header = "🪙 Asset   💵 Price   🕒 Checked   🕐 1h   🕕 6h   🕛 12h"
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [
                    paint_line(header, body_cfg.get("column_header_text_color", "")),
                    color_if_plain("(no prices)", body_cfg.get("body_text_color", "")),
                ],
            )
        )
        lines.extend(body_pad_below(PANEL_SLUG))
        return lines

    # Compute trends using PriceMonitor history (prices table)
    try:
        trend_map = _price_trends.compute_price_trends(
            ctx.get("dl") or ctx,
            items,
        )
    except Exception:
        trend_map = {}

    table_lines = _build_rich_table(items, trend_map, body_cfg, width)

    if not table_lines:
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [color_if_plain("(no prices)", body_cfg.get("body_text_color", ""))],
            )
        )
        lines.extend(body_pad_below(PANEL_SLUG))
        return lines

    header_line = table_lines[0]
    data_lines = table_lines[1:]

    # Tint header like other panels
    lines.extend(
        body_indent_lines(
            PANEL_SLUG,
            [paint_line(header_line, body_cfg.get("column_header_text_color", ""))],
        )
    )
    for ln in data_lines:
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [color_if_plain(ln, body_cfg.get("body_text_color", ""))],
            )
        )

    lines.extend(body_pad_below(PANEL_SLUG))
    return lines


def connector(*args, **kwargs) -> List[str]:
    return render(*args, **kwargs)


def name() -> str:
    return PANEL_NAME


if __name__ == "__main__":
    demo = [
        {
            "symbol": "BTC",
            "price": 118755.0,
            "checked_ts": _dt.datetime.now().isoformat(timespec="seconds"),
        },
        {
            "symbol": "SOL",
            "price": 138.17,
            "checked_ts": _dt.datetime.now().isoformat(timespec="seconds"),
        },
    ]
    for ln in render({"prices": demo}):
        print(ln)
