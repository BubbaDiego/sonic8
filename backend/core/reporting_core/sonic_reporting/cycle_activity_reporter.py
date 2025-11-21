# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Mapping, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich import box

from .console_panels.theming import (  # type: ignore
    emit_title_block,
    get_panel_body_config,
    body_pad_above,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
    paint_line,
    console_width as _theme_width,
)

PANEL_SLUG = "activity"
PANEL_NAME = "Cycle Activity"


# ───────────────────────── width helper ───────────────────────── #


def _console_width(default: int = 92) -> int:
    """Resolve console width via shared theming, with sane bounds."""
    try:
        return int(_theme_width(default))
    except Exception:
        return default


# ───────────────────────── basic util ───────────────────────── #


def _secs(ms: Any) -> str:
    """Format milliseconds as seconds with 2 decimals (or empty string)."""
    try:
        if ms is None:
            return ""
        return f"{float(ms) / 1000:.2f}"
    except Exception:
        return ""


ICON_MAP: Dict[str, str] = {
    "thresholds": "⚙️",
    "cyclone": "🌀",
    "raydium": "🪙",
    "hedges": "🪶",
    "liquid": "💧",
    "profit": "💰",
    "market": "📈",
    "xcom": "⚙️",
    "heartbeat": "💓",
}

STATUS_ICON: Dict[str, str] = {
    "ok": "✅",
    "success": "✅",
    "warn": "⚠️",
    "warning": "⚠️",
    "error": "✖️",
    "fail": "✖️",
    "skip": "⚪",
}


def _phase_icon(phase: str) -> str:
    key = (phase or "").lower().strip()
    for name, icon in ICON_MAP.items():
        if name in key:
            return icon
    return "⚙️"


def _status_cell(raw: Any) -> str:
    key = str(raw or "").lower().strip()
    icon = STATUS_ICON.get(key, "✅")
    if key in ("ok", "success", ""):
        return f"[green]{icon}[/]"
    if key in ("warn", "warning"):
        return f"[yellow]{icon}[/]"
    if key in ("error", "fail"):
        return f"[red]{icon}[/]"
    if key == "skip":
        return f"[grey50]{icon}[/]"
    return icon


# ───────────────────────── data access ───────────────────────── #


def _latest_cycle_id(dl: Any) -> Optional[str]:
    """
    Return the most recent cycle_id from cycle_activities, or None.
    """
    db = getattr(dl, "db", None)
    if db is None or not hasattr(db, "get_cursor"):
        return None

    try:
        cur = db.get_cursor()
        cur.execute("SELECT MAX(cycle_id) FROM cycle_activities")
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else None
    except Exception:
        return None


def _rows_for_cycle(dl: Any, cycle_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all activity rows for a given cycle_id as dicts.
    """
    db = getattr(dl, "db", None)
    if db is None or not hasattr(db, "get_cursor"):
        return []

    try:
        cur = db.get_cursor()
        cur.execute(
            "SELECT * FROM cycle_activities WHERE cycle_id=? ORDER BY id ASC",
            (cycle_id,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []


# ───────────────────────── Rich plumbing ───────────────────────── #


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


def _extract_config_line(
    rows: List[Dict[str, Any]],
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Look for a Thresholds row whose outcome/notes starts with 'JSON=' and
    pull that string out so we can show it above the table instead of
    inside the Outcome column.

    Returns (config_line, normalized_rows).
    """
    config_line: Optional[str] = None
    normalized: List[Dict[str, Any]] = []

    for r in rows:
        d = dict(r)  # shallow copy
        outcome = d.get("notes") or d.get("outcome") or ""
        if (
            isinstance(outcome, str)
            and outcome.startswith("JSON=")
            and config_line is None
        ):
            config_line = outcome.strip()
            # keep the table narrow by shortening the outcome text
            d["notes"] = "JSON config"
            d["outcome"] = "JSON config"
        normalized.append(d)

    return config_line, normalized


def _build_rich_table(
    rows: List[Dict[str, Any]],
    body_cfg: Dict[str, Any],
    width: int,
) -> List[str]:
    """
    Build a Rich table for the Cycle Activity rows and return it as a list
    of styled text lines, aligned to the configured width.
    """
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

    table.add_column("Activity", justify="left", no_wrap=True)
    table.add_column("Outcome", justify="left")
    table.add_column("Status", justify="center", no_wrap=True)
    table.add_column("Elapsed", justify="right", no_wrap=True)

    for r in rows:
        phase = str(r.get("phase") or r.get("activity") or "").strip() or "—"
        icon = _phase_icon(phase)
        label = str(r.get("label") or phase).strip()
        activity_cell = f"{icon} {label}".strip()

        outcome = r.get("notes") or r.get("outcome") or ""
        outcome_str = str(outcome)

        status_key = r.get("status") or r.get("state") or outcome or "ok"
        status_cell = _status_cell(status_key)

        elapsed = _secs(r.get("duration_ms"))

        table.add_row(activity_cell, outcome_str, status_cell, elapsed or "")

    buf = StringIO()
    console = Console(record=True, width=width, file=buf, force_terminal=True)
    console.print(table)

    text = console.export_text(styles=True).rstrip("\n")
    if not text:
        return []

    raw_lines = text.splitlines()
    return _justify_lines(raw_lines, table_cfg["table_justify"], width)


# ───────────────────────── render ───────────────────────── #


def render(dl, *_unused, default_json_path=None) -> None:
    """
    Classic entrypoint: render(dl, ...)

    Called via _safe_render(...) in the Sonic console runner.
    """
    cid = _latest_cycle_id(dl)

    print()
    for ln in emit_title_block(PANEL_SLUG, PANEL_NAME):
        print(ln)

    body_cfg = get_panel_body_config(PANEL_SLUG)
    body_color = body_cfg.get("body_text_color", "")
    header_color = body_cfg.get("column_header_text_color", "")

    if not cid:
        for ln in body_pad_above(PANEL_SLUG):
            print(ln)
        for ln in body_indent_lines(
            PANEL_SLUG,
            [color_if_plain("(no activity yet)", body_color)],
        ):
            print(ln)
        for ln in body_pad_below(PANEL_SLUG):
            print(ln)
        return

    rows = _rows_for_cycle(dl, cid)
    if not rows:
        for ln in body_pad_above(PANEL_SLUG):
            print(ln)
        for ln in body_indent_lines(
            PANEL_SLUG,
            [color_if_plain("(no activity yet)", body_color)],
        ):
            print(ln)
        for ln in body_pad_below(PANEL_SLUG):
            print(ln)
        return

    # Pull JSON config line out of the table rows
    config_line, table_rows = _extract_config_line(rows)

    width = _console_width()
    table_lines = _build_rich_table(table_rows, body_cfg, width)
    if not table_lines:
        for ln in body_pad_above(PANEL_SLUG):
            print(ln)
        for ln in body_indent_lines(
            PANEL_SLUG,
            [color_if_plain("(no activity yet)", body_color)],
        ):
            print(ln)
        for ln in body_pad_below(PANEL_SLUG):
            print(ln)
        return

    header_line = table_lines[0]
    data_lines = table_lines[1:]

    # Top padding
    for ln in body_pad_above(PANEL_SLUG):
        print(ln)

    # Config line (icon + JSON=...), then a blank spacer line
    if config_line:
        # 🔧 changed: drop the literal word 'Configuration'
        cfg_text = f"⚙️ {config_line}"
        cfg_painted = paint_line(cfg_text, header_color)
        for ln in body_indent_lines(PANEL_SLUG, [cfg_painted]):
            print(ln)

        for ln in body_indent_lines(PANEL_SLUG, [""]):
            print(ln)

    # Header row
    for ln in body_indent_lines(
        PANEL_SLUG,
        [paint_line(header_line, header_color)],
    ):
        print(ln)

    # Body rows
    for raw in data_lines:
        for ln in body_indent_lines(
            PANEL_SLUG,
            [color_if_plain(raw, body_color)],
        ):
            print(ln)

    # Bottom padding
    for ln in body_pad_below(PANEL_SLUG):
        print(ln)
