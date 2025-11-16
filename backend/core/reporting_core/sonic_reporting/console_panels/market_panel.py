# -*- coding: utf-8 -*-
"""Market Alerts panel (Rich-powered thin table with safe fallback)."""
from __future__ import annotations

import json
from io import StringIO
from typing import Any, Dict, Iterable, List, Optional

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
)

# HR_WIDTH is used to bound the Rich table width; fall back if missing
try:
    from .theming import HR_WIDTH
except Exception:  # pragma: no cover
    HR_WIDTH = 80

# Try to import Rich – if missing, we fall back to plain string layout
try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except Exception:  # pragma: no cover
    Console = None  # type: ignore
    Table = None    # type: ignore
    RICH_AVAILABLE = False


PANEL_SLUG = "market"
PANEL_NAME = "Market Alerts"


# ───────────────────────── DL + monitor rows ──────────────────────────


def _resolve_dl(ctx: Any) -> Any:
    if ctx is None:
        return None
    if isinstance(ctx, dict):
        dl = ctx.get("dl")
        if dl is not None:
            return dl
    return getattr(ctx, "dl", None)


def _get_monitor_rows(dl: Any) -> List[Dict[str, Any]]:
    """
    Robustly pull monitor rows from dl.monitors / dl_dl_monitors.

    This mirrors the original logic you had – no behavior changes here.
    """
    if dl is None:
        return []
    mgr = getattr(dl, "monitors", None) or getattr(dl, "dl_monitors", None)
    if mgr is None:
        return []

    candidates: Iterable[Any] = []
    for name in (
        "select_all",
        "list_all",
        "all",
        "latest",
        "list_latest",
        "latest_rows",
        "get_latest",
    ):
        fn = getattr(mgr, name, None)
        if callable(fn):
            try:
                data = fn()
            except TypeError:
                continue
            if data:
                candidates = data
                break
    else:
        direct = getattr(mgr, "rows", None)
        if direct:
            candidates = direct

    rows: List[Dict[str, Any]] = []
    for row in candidates:
        if isinstance(row, dict):
            rows.append(dict(row))
            continue
        norm: Dict[str, Any] = {}
        for key in (
            "monitor",
            "label",
            "state",
            "value",
            "unit",
            "thr_op",
            "thr_value",
            "thr_unit",
            "source",
            "meta",
        ):
            if hasattr(row, key):
                norm[key] = getattr(row, key)
        rows.append(norm)
    return rows


def _normalize_meta(meta: Any) -> Dict[str, Any]:
    if isinstance(meta, dict):
        return dict(meta)
    if isinstance(meta, str):
        try:
            data = json.loads(meta)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def _market_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        monitor = (row.get("monitor") or "").lower()
        if monitor != "market":
            continue
        row = dict(row)
        row["meta"] = _normalize_meta(row.get("meta"))
        out.append(row)
    return out


# ───────────────────────── formatting helpers ─────────────────────────


def _fmt_price(val: Any) -> str:
    if val is None:
        return "–"
    try:
        return f"{float(val):.2f}"
    except Exception:
        return str(val)


def _fmt_move_abs(val: Any) -> str:
    """Signed absolute move in price units."""
    if val is None:
        return "–"
    try:
        v = float(val)
        sign = "+" if v >= 0 else "-"
        return f"{sign}{abs(v):.2f}"
    except Exception:
        return str(val)


def _fmt_pct(val: Any) -> str:
    if val is None:
        return "–"
    try:
        v = float(val)
        sign = "+" if v >= 0 else "-"
        return f"{sign}{abs(v):.2f}%"
    except Exception:
        return str(val)


def _fmt_threshold(meta: Dict[str, Any], thr_value: Any) -> str:
    # Prefer explicit description if present
    desc = meta.get("threshold_desc") or meta.get("desc")
    if isinstance(desc, str) and desc.strip():
        return desc.strip()

    if thr_value is None:
        return "–"

    try:
        v = float(thr_value)
        return f"${v:.2f} move"
    except Exception:
        return str(thr_value)


def _fmt_bar(meta: Dict[str, Any]) -> str:
    try:
        prox = float(meta.get("proximity") or 0.0)
    except Exception:
        prox = 0.0
    prox = max(0.0, min(prox, 1.0))
    filled = int(round(prox * 10))
    filled = max(0, min(filled, 10))
    return "▰" * filled + "▱" * (10 - filled)


def _asset_from_row(row: Dict[str, Any]) -> str:
    meta = row.get("meta") or {}
    asset = row.get("asset") or meta.get("asset") or row.get("label") or ""
    asset = str(asset).strip()
    return asset or "—"


def _entry_price(meta: Dict[str, Any]) -> Any:
    """
    Entry (anchor) price:

    We trust Market Core to give us an explicit anchor from PriceAlert:
      • meta["anchor_price"]        (current anchor)
      • meta["original_anchor_price"] as fallback
    """
    anchor = meta.get("anchor_price")
    if anchor is not None:
        return anchor
    origin = meta.get("original_anchor_price")
    if origin is not None:
        return origin
    return None


def _current_price(meta: Dict[str, Any]) -> Any:
    return meta.get("price") or meta.get("current_price")


def _move_abs(meta: Dict[str, Any]) -> Any:
    mv = meta.get("move_abs")
    if mv is not None:
        return mv
    price = _current_price(meta)
    anchor = _entry_price(meta)
    try:
        if price is not None and anchor not in (None, 0):
            return float(price) - float(anchor)
    except Exception:
        pass
    return None


def _move_pct(meta: Dict[str, Any]) -> Any:
    mv = meta.get("move_pct")
    if mv is not None:
        return mv
    price = _current_price(meta)
    anchor = _entry_price(meta)
    try:
        if price is not None and anchor not in (None, 0):
            return (float(price) - float(anchor)) / float(anchor) * 100.0
    except Exception:
        pass
    return None


def _fmt_move_value(meta: Dict[str, Any]) -> str:
    """
    Generic 'Move' column:

    - If rule_type is percent (e.g. move_pct), show percent.
    - Otherwise, show dollar move.
    """
    rule_type = (meta.get("rule_type") or "").lower()
    if "pct" in rule_type:
        return _fmt_pct(_move_pct(meta))
    return _fmt_move_abs(_move_abs(meta))


# ───────────────────────── rich table builder ─────────────────────────


def _build_rich_table_lines(rows: List[Dict[str, Any]], *, width: Optional[int]) -> List[str]:
    """
    Build a thin Rich table and return its rendered lines as plain strings.
    If Rich isn't available, returns an empty list.
    """
    if not RICH_AVAILABLE or Table is None or Console is None:
        return []

    table = Table(
        show_header=True,
        header_style="bold cyan",
        show_lines=False,
        box=None,          # thin, borderless table
        pad_edge=False,
        expand=False,
    )

    table.add_column("Asset", justify="left", no_wrap=True)
    table.add_column("Entry", justify="right")
    table.add_column("Current", justify="right")
    table.add_column("Move", justify="right")
    table.add_column("Thr", justify="left")
    table.add_column("Prox", justify="left", no_wrap=True)
    table.add_column("State", justify="left")

    for row in rows:
        meta = row.get("meta") or {}
        asset = _asset_from_row(row)

        entry = _fmt_price(_entry_price(meta))
        current = _fmt_price(_current_price(meta))
        move_str = _fmt_move_value(meta)
        thr_str = _fmt_threshold(meta, row.get("thr_value"))
        bar = _fmt_bar(meta)
        state = str(row.get("state") or "").upper()

        table.add_row(
            asset,
            entry,
            current,
            move_str,
            thr_str,
            bar,
            state,
        )

    buf = StringIO()
    console = Console(
        file=buf,
        width=width or HR_WIDTH,
        force_terminal=False,
        color_system=None,
    )
    console.print(table)
    text = buf.getvalue().rstrip("\n")
    return text.splitlines() if text else []


# ───────────────────────── fallback string table ──────────────────────


def _build_plain_table_lines(rows: List[Dict[str, Any]]) -> List[str]:
    """
    Fallback layout when Rich is not available.

    Simple, aligned ASCII table:
      Asset  Entry      Current     Move      Thr          Prox       State
    """
    lines: List[str] = []
    header = "Asset   Entry      Current     Move      Thr          Prox       State"
    lines.append(header)
    lines.append("-" * len(header))

    for row in rows:
        meta = row.get("meta") or {}

        asset = _asset_from_row(row)
        entry = _fmt_price(_entry_price(meta))
        current = _fmt_price(_current_price(meta))
        move_str = _fmt_move_value(meta)
        thr_str = _fmt_threshold(meta, row.get("thr_value"))
        bar = _fmt_bar(meta)
        state = str(row.get("state") or "").upper()

        line = (
            f"{asset:<6} "
            f"{entry:>10} "
            f"{current:>10} "
            f"{move_str:>10} "
            f"{thr_str:<12} "
            f"{bar:<11} "
            f"{state:<6}"
        )
        lines.append(line)

    return lines


# ───────────────────────── panel API ─────────────────────────


def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    dl = _resolve_dl(context)
    body_cfg = get_panel_body_config(PANEL_SLUG)
    lines: List[str] = []

    # Title (icons only in title; table itself is clean)
    lines += emit_title_block(PANEL_SLUG, PANEL_NAME)

    if dl is None:
        note = color_if_plain(
            "  (no DataLocker context)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])
        lines += body_pad_below(PANEL_SLUG)
        return lines

    rows = _market_rows(_get_monitor_rows(dl))

    if not rows:
        header = color_if_plain(
            "  Asset   Entry      Current     Move      Thr          Prox       State",
            body_cfg["column_header_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [header])
        note = color_if_plain(
            "  (no active market alerts)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])
        lines += body_pad_below(PANEL_SLUG)
        return lines

    # Prefer Rich table; fall back to plain layout if Rich is unavailable
    table_lines: List[str]
    if RICH_AVAILABLE:
        table_lines = _build_rich_table_lines(rows, width=width)
        if not table_lines:
            table_lines = _build_plain_table_lines(rows)
    else:
        table_lines = _build_plain_table_lines(rows)

    # Apply body color + indentation
    colored_lines = [
        color_if_plain(f"  {ln}", body_cfg["body_text_color"])
        for ln in table_lines
    ]
    lines += body_indent_lines(PANEL_SLUG, colored_lines)

    lines += body_pad_below(PANEL_SLUG)
    return lines


def connector(dl=None, ctx: Optional[Dict[str, Any]] = None, width: Optional[int] = None) -> List[str]:
    context: Dict[str, Any] = dict(ctx or {})
    if dl is not None:
        context.setdefault("dl", dl)
    return render(context, width=width)
