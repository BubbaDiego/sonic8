# -*- coding: utf-8 -*-
"""Monitors panel – Rich-powered table with configurable style."""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from rich.console import Console
from rich.table import Table
from rich import box

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
)

try:
    from .theming import HR_WIDTH
except Exception:  # fallback
    HR_WIDTH = 100

PANEL_SLUG = "monitors"
PANEL_NAME = "Monitors"


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
    Same robust monitor row fetch as in market_panel, but we keep all monitors.
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
            "age_secs",
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


def _normalized_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        r["meta"] = _normalize_meta(row.get("meta"))
        out.append(r)
    return out


# ───────────────────────── formatting helpers ─────────────────────────


def _fmt_monitor_name(row: Dict[str, Any]) -> str:
    label = row.get("label")
    mon = row.get("monitor")
    if label and label != mon:
        return f"{label}"
    return mon or "—"


def _fmt_threshold(row: Dict[str, Any]) -> str:
    op = (row.get("thr_op") or "").strip()
    val = row.get("thr_value")
    unit = (row.get("thr_unit") or "").strip()
    if val is None:
        return "—"
    try:
        v = float(val)
        value_str = f"{v:.2f}"
    except Exception:
        value_str = str(val)
    if unit:
        value_str = f"{value_str} {unit}"
    if op:
        return f"{op} {value_str}"
    return value_str


def _fmt_value(row: Dict[str, Any]) -> str:
    val = row.get("value")
    if val is None:
        return "—"
    try:
        return f"{float(val):.3g}"
    except Exception:
        return str(val)


def _fmt_state(row: Dict[str, Any]) -> str:
    s = str(row.get("state") or "").upper()
    if s == "BREACH":
        return "[red]BREACH[/]"
    if s == "WARN":
        return "[yellow]WARN[/]"
    if s == "OK":
        return "[green]OK[/]"
    return s or "–"


def _fmt_source(row: Dict[str, Any]) -> str:
    return str(row.get("source") or "").strip() or "–"


# ───────────────────────── table config helpers ───────────────────────


def _resolve_table_cfg(body_cfg: Dict[str, Any]) -> Dict[str, Any]:
    raw = body_cfg.get("table") or {}
    if not isinstance(raw, dict):
        raw = {}
    style = (raw.get("style") or "invisible").lower()
    table_justify = (raw.get("table_justify") or "left").lower()
    header_justify = (raw.get("header_justify") or "left").lower()
    return {
        "style": style,
        "table_justify": table_justify,
        "header_justify": header_justify,
    }


def _style_to_box(style: str) -> (Any, bool):
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
            else:  # right
                left = pad
            out.append(" " * left + s)
    return out


# ───────────────────────── Rich table builder ─────────────────────────


def _build_rich_table(rows: List[Dict[str, Any]], table_cfg: Dict[str, Any]) -> List[str]:
    box_style, show_lines = _style_to_box(table_cfg.get("style"))

    table = Table(
        show_header=True,
        header_style="",
        show_lines=show_lines,
        box=box_style,
        pad_edge=False,
        expand=False,
    )

    # Icons in header; data rows plain text
    table.add_column("Mon", justify="left", no_wrap=True)
    table.add_column("Thresh", justify="left")
    table.add_column("Value", justify="right")
    table.add_column("State", justify="left")
    table.add_column("Source", justify="left")

    for row in rows:
        name = _fmt_monitor_name(row)
        thresh = _fmt_threshold(row)
        val = _fmt_value(row)
        state = _fmt_state(row)
        source = _fmt_source(row)

        table.add_row(
            name,
            thresh,
            val,
            state,
            source,
        )

    console = Console(record=True, width=HR_WIDTH, force_terminal=True)
    console.print(table)
    text = console.export_text().rstrip("\n")
    lines = text.splitlines() if text else []

    lines = _justify_lines(lines, table_cfg.get("table_justify"), HR_WIDTH)
    return lines


# ───────────────────────── panel API ─────────────────────────


def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    dl = _resolve_dl(context)
    body_cfg = get_panel_body_config(PANEL_SLUG)
    table_cfg = _resolve_table_cfg(body_cfg)
    lines: List[str] = []

    # Title
    lines += emit_title_block(PANEL_SLUG, PANEL_NAME)

    if dl is None:
        note = color_if_plain(
            "  (no DataLocker context)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])
        lines += body_pad_below(PANEL_SLUG)
        return lines

    rows = _normalized_rows(_get_monitor_rows(dl))

    if not rows:
        header = "Mon   Thresh      Value   State   Source"
        header_colored = color_if_plain(
            "  " + header,
            body_cfg["column_header_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [header_colored])

        note = color_if_plain(
            "  (no monitors to display)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])
        lines += body_pad_below(PANEL_SLUG)
        return lines

    table_lines = _build_rich_table(rows, table_cfg)

    if table_lines:
        header_line = table_lines[0]
        data_lines = table_lines[1:]
        lines += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain(header_line, body_cfg["column_header_text_color"])],
        )
        for ln in data_lines:
            lines += body_indent_lines(
                PANEL_SLUG,
                [color_if_plain(ln, body_cfg["body_text_color"])],
            )
    else:
        note = color_if_plain(
            "  (no monitor data to display)",
            body_cfg["body_text_color"],
        )
        lines += body_indent_lines(PANEL_SLUG, [note])

    lines += body_pad_below(PANEL_SLUG)
    return lines


def connector(
    dl: Any = None,
    ctx: Optional[Dict[str, Any]] = None,
    width: Optional[int] = None,
) -> List[str]:
    context: Dict[str, Any] = dict(ctx or {})
    if dl is not None:
        context.setdefault("dl", dl)
    return render(context, width=width)
