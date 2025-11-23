from __future__ import annotations
"""
raydium_panel.py
Sonic Reporting — Raydium LPs panel (console)

Style parity with other panels:
- centered title rail
- solid rule above column headers
- tidy columns, total row, checked-at stamp

Call-shape safe:
- connector(dl, ctx, width)  ← preferred by console_reporter
- connector(ctx) / connector(ctx, width)
- render(ctx, **kw)
Both always return List[str].
"""

import datetime as _dt
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich import box

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
    paint_line,
)
from backend.core.raydium_core.console.raydium_console import (
    RaydiumClPosition,
    fetch_raydium_cl_positions,
    raydium_cl_positions_from_payload,
)

try:
    from .theming import HR_WIDTH  # type: ignore
except Exception:  # pragma: no cover
    HR_WIDTH = 100

PANEL_KEY = "raydium_panel"
PANEL_SLUG = "raydium"
PANEL_NAME = "Raydium LPs"
RAYDIUM_PANEL_TITLE = "🌊 Raydium LPs"


def _abbr_middle(s: Any, front: int = 6, back: int = 6, min_len: int = 12) -> str:
    s = ("" if s is None else str(s)).strip()
    if len(s) <= min_len or len(s) <= front + back + 3:
        return s
    return f"{s[:front]}…{s[-back:]}"


def _fmt_usd(v: Any) -> str:
    try:
        x = float(v)
        return f"${int(round(x)):,}" if abs(x - round(x)) < 1e-6 else f"${x:,.2f}"
    except Exception:
        return "—"


def _fmt_lp(v: Any) -> str:
    if v in (None, "", 0, 0.0):
        return "—"
    try:
        x = float(v)
        if x == 0:
            return "—"
        if abs(x) < 0.001: return f"{x:.4f}"
        if abs(x) < 1:     return f"{x:.3f}"
        return f"{x:.2f}"
    except Exception:
        return str(v)


def _fmt_apr(v: Any) -> str:
    try:
        x = float(v)
        return f"{x:.1f}%"
    except Exception:
        return "—"


def _fmt_time(ts: Any) -> str:
    if ts is None:
        dt = _dt.datetime.now()
    elif isinstance(ts, (int, float)):
        dt = _dt.datetime.fromtimestamp(float(ts))
    elif isinstance(ts, _dt.datetime):
        dt = ts
    else:
        s = str(ts).strip()
        try:
            if s.endswith("Z"):
                dt = _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
            else:
                dt = _dt.datetime.fromisoformat(s)
        except Exception:
            dt = _dt.datetime.now()
    hour = dt.strftime("%I").lstrip("0") or "0"
    return f"{hour}:{dt.strftime('%M%p').lower()}"


# ────────────────────────────────────────────────────────────────────────────────
# Data normalization
# ────────────────────────────────────────────────────────────────────────────────

def _norm_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    if rec is None:
        rec = {}
    pool = rec.get("pool") or rec.get("pool_name") or rec.get("amm") or rec.get("pair") \
           or rec.get("symbol") or rec.get("collection") or ""
    address = rec.get("address") or rec.get("owner") or rec.get("pubkey") or rec.get("mint") or ""
    lp_qty = rec.get("lp_qty") or rec.get("qty") or rec.get("balance") or rec.get("amount") or rec.get("raw_amount")
    usd_value = rec.get("usd_value") or rec.get("usd") or rec.get("value_usd") or rec.get("fiat_value") or 0.0
    apr = rec.get("apr") or rec.get("apy") or rec.get("est_apr")
    checked_ts = rec.get("checked_ts") or rec.get("ts") or rec.get("timestamp")
    return {
        "pool": str(pool) if pool is not None else "",
        "address": str(address) if address is not None else "",
        "lp_qty": lp_qty,
        "usd_value": usd_value,
        "apr": apr,
        "checked_ts": checked_ts,
    }


def _record_from_position(pos: RaydiumClPosition) -> Dict[str, Any]:
    return {
        "pool": pos.pool_label,
        "address": pos.address or pos.position_label,
        "lp_qty": pos.position_label or f"{pos.token_a_symbol} / {pos.token_b_symbol}",
        "usd_value": pos.usd_value,
        "apr": pos.apr_label,
        "checked_ts": None,
    }


def _records_from_positions(positions: List[RaydiumClPosition]) -> List[Dict[str, Any]]:
    return [_norm_record(_record_from_position(p)) for p in positions]


def _positions_from_payload(payload: Any) -> List[Dict[str, Any]]:
    positions = raydium_cl_positions_from_payload(payload)
    return _records_from_positions(positions) if positions else []


def _coalesce(*vals, default=None):
    for v in vals:
        if v not in (None, ""):
            return v
    return default


def _collect_records(ctx: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """
    Try sources in order:
      1) ctx['records'] or ctx['raydium'] (list/dict)
      2) ctx['csum']['raydium']['records'|'lps']
      3) dl.raydium.* helpers
    """
    # 1) direct feed
    direct = ctx.get("records")
    if isinstance(direct, list) and direct:
        return [_norm_record(r or {}) for r in direct], "ctx.records"

    rayd = ctx.get("raydium")
    if isinstance(rayd, list) and rayd:
        return [_norm_record(r or {}) for r in rayd], "ctx.raydium"
    if isinstance(rayd, dict):
        seq = rayd.get("records") or rayd.get("positions") or rayd.get("lps") or []
        if isinstance(seq, list) and seq:
            return [_norm_record(r or {}) for r in seq], "ctx.raydium.records"

    for key in ("raydium_payload", "raydium_positions_payload", "raydium_positions", "raydium_rows"):
        payload = ctx.get(key)
        if payload:
            recs = _positions_from_payload(payload)
            if recs:
                return recs, f"ctx.{key}"

    # 2) from summary
    csum = ctx.get("csum") or ctx.get("summary") or {}
    seq = _coalesce((csum.get("raydium") or {}).get("records"),
                    (csum.get("raydium") or {}).get("lps"),
                    default=None)
    if isinstance(seq, list) and seq:
        return [_norm_record(r or {}) for r in seq], "csum.raydium"

    # 3) DataLocker provider
    dl = ctx.get("dl")

    sys_mgr = getattr(dl, "system", None)
    if sys_mgr and hasattr(sys_mgr, "get_var"):
        try:
            sys_payload = sys_mgr.get_var("raydium_positions")
        except Exception:
            sys_payload = None
        if sys_payload:
            recs = _positions_from_payload(sys_payload)
            if recs:
                return recs, "dl.system.raydium_positions"

    owner = ctx.get("owner") or ctx.get("raydium_owner")
    if owner:
        try:
            positions = fetch_raydium_cl_positions(
                str(owner),
                mints=ctx.get("raydium_mints"),
                price_url=ctx.get("raydium_price_url"),
            )
            recs = _records_from_positions(positions)
            if recs:
                return recs, "raydium_console_helper"
        except Exception:
            pass

    provider = getattr(dl, "raydium", None)
    if provider:
        for name in ("get_latest_lp_positions", "get_lp_positions", "get_positions",
                     "list_lp_nfts", "list_positions"):
            fn = getattr(provider, name, None)
            if callable(fn):
                try:
                    res = fn()
                    arr = (res.get("records") if isinstance(res, dict) else res)
                    if isinstance(arr, list) and arr:
                        return [_norm_record(r or {}) for r in arr], f"dl.raydium.{name}()"
                except Exception:
                    pass
        # attributes
        for attr in ("records", "positions", "lps", "items"):
            arr = getattr(provider, attr, None)
            if isinstance(arr, list) and arr:
                return [_norm_record(r or {}) for r in arr], f"dl.raydium.{attr}"

    return [], "none"


# ────────────────────────────────────────────────────────────────────────────────
# Table helpers
# ────────────────────────────────────────────────────────────────────────────────


def _style_to_box(style: str) -> tuple[Any, bool]:
    style = (style or "invisible").lower()
    if style == "thin":
        return box.SIMPLE_HEAD, False
    if style == "thick":
        return box.HEAVY_HEAD, True
    return None, False


def _justify_lines(lines: List[str], justify: str, width: int) -> List[str]:
    justify = (justify or "left").lower()
    if justify not in ("center", "right"):
        return lines
    if not lines:
        return lines

    out: List[str] = []
    for line in lines:
        s = line.rstrip("\n")
        pad = width - len(s)
        if pad <= 0:
            out.append(s)
        else:
            if justify == "center":
                left = pad // 2
                right = pad - left
                out.append((" " * left) + s + (" " * right))
            else:  # right
                out.append((" " * pad) + s)
    return out


def _resolve_table_cfg(body_cfg: Dict[str, Any]) -> Dict[str, str]:
    table_cfg = body_cfg.get("table") if isinstance(body_cfg.get("table"), dict) else {}
    style = str(table_cfg.get("style", "invisible")).lower()
    table_justify = str(table_cfg.get("table_justify", "left")).lower()
    header_justify = str(table_cfg.get("header_justify", "left")).lower()
    return {
        "style": style,
        "table_justify": table_justify,
        "header_justify": header_justify,
    }


def _build_rich_table(records: List[Dict[str, Any]], table_cfg: Dict[str, str]) -> List[str]:
    box_style, show_lines = _style_to_box(table_cfg.get("style", ""))

    table = Table(
        show_header=True,
        header_style="",
        show_lines=show_lines,
        box=box_style,
        show_edge=False,
        pad_edge=False,
        expand=False,
    )

    table.add_column("Pool", justify=table_cfg.get("header_justify", "left"), no_wrap=True)
    table.add_column("Address", justify=table_cfg.get("header_justify", "left"), no_wrap=True)
    table.add_column("LP", justify="right", no_wrap=True)
    table.add_column("USD", justify="right", no_wrap=True)
    table.add_column("APR", justify="right", no_wrap=True)
    table.add_column("Checked", justify="left", no_wrap=True)

    for rec in records:
        table.add_row(
            _abbr_middle(rec.get("pool", ""), 6, 6, 22),
            _abbr_middle(rec.get("address", ""), 6, 6, 24),
            _fmt_lp(rec.get("lp_qty")),
            _fmt_usd(rec.get("usd_value")),
            _fmt_apr(rec.get("apr")),
            _fmt_time(rec.get("checked_ts")) if rec.get("checked_ts") else "",
        )

    buf = StringIO()
    console = Console(record=True, width=HR_WIDTH, file=buf, force_terminal=True)
    console.print(table)

    text = console.export_text().rstrip("\n")
    lines = text.splitlines() if text else []
    return _justify_lines(lines, table_cfg.get("table_justify", "left"), HR_WIDTH)


# ────────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────────

def connector(dl=None, ctx: Optional[Dict[str, Any]] = None, width: Optional[int] = None, **kw) -> List[str]:
    """
    Preferred entrypoint from console_reporter.
    Normalizes everything into a single ctx dict and delegates to render().
    Always returns List[str].
    """
    # `ctx` might be passed positionally or via kw; reconcile:
    if ctx is None and "context" in kw and isinstance(kw["context"], dict):
        ctx = kw.pop("context")

    ctx_dict: Dict[str, Any] = {}
    if isinstance(ctx, dict):
        ctx_dict.update(ctx)
    # propagate dl/width and any extras
    if dl is not None:
        ctx_dict["dl"] = dl
    if width is not None:
        ctx_dict["width"] = width
    ctx_dict.update(kw)
    lines = render(ctx_dict)
    return lines if isinstance(lines, list) else [str(lines)]


def render(context: Optional[Dict[str, Any]] = None, **kwargs) -> List[str]:
    """
    Legacy-friendly renderer; accepts a single ctx dict (preferred).
    Returns List[str].
    """
    ctx: Dict[str, Any] = {}
    if isinstance(context, dict):
        ctx.update(context)
    ctx.update(kwargs)

    body_cfg = get_panel_body_config(PANEL_SLUG)
    table_cfg = _resolve_table_cfg(body_cfg)

    lines: List[str] = []
    lines += emit_title_block(PANEL_SLUG, RAYDIUM_PANEL_TITLE)

    records, source = _collect_records(ctx)

    total_usd = 0.0
    last_ts = None

    if isinstance(records, list):
        for rec in records:
            total_usd += float(rec.get("usd_value") or 0.0)
            ts = rec.get("checked_ts")
            if ts:
                last_ts = ts

    table_lines = _build_rich_table(records if isinstance(records, list) else [], table_cfg)

    if table_lines:
        header_line = table_lines[0]
        data_lines = table_lines[1:]
        lines += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain(header_line, body_cfg.get("column_header_text_color", "default"))],
        )
        for ln in data_lines:
            lines += body_indent_lines(
                PANEL_SLUG,
                [color_if_plain(ln, body_cfg.get("body_text_color", "default"))],
            )

    if not records:
        note = color_if_plain(
            "  (no raydium positions)",
            body_cfg.get("body_text_color", "default"),
        )
        lines += body_indent_lines(PANEL_SLUG, [note])

    totals_color = body_cfg.get("totals_row_color", "default")
    lines += body_indent_lines(
        PANEL_SLUG,
        [
            paint_line(f"  Total (USD): {_fmt_usd(total_usd)}", totals_color),
            paint_line(
                f"  Checked: {_fmt_time(last_ts) if last_ts else _fmt_time(None)}",
                totals_color,
            ),
            color_if_plain(
                f"  [RAY] source={source} count={len(records) if isinstance(records, list) else 0}",
                body_cfg.get("body_text_color", "default"),
            ),
        ],
    )

    lines += body_pad_below(PANEL_SLUG)
    return lines


def name() -> str:
    return PANEL_NAME


if __name__ == "__main__":
    demo = [{
        "pool": "So111111…/EPjF…",
        "address": "2jn9ve…dSU9pj",
        "lp_qty": 1.23456,
        "usd_value": 106,
        "apr": None,
        "checked_ts": _dt.datetime.now().isoformat(timespec="seconds"),
    }]
    for ln in connector(ctx={"records": demo}, width=92):
        print(ln)
