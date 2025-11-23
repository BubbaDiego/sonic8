# -*- coding: utf-8 -*-
from __future__ import annotations

"""
risk_panel.py
Sonic Reporting — Risk Snapshot panel (console, Look 2)

Metrics:
- Total Heat:   size-weighted avg of per-position heat_index (NOT a %)
- Total Lev:    size-weighted avg leverage
- Total Travel: size-weighted avg travel_percent
- Balance:      SHORT vs LONG by notional size (40-seg bar; 4 seg = 10%)
"""

import logging
from io import StringIO
from typing import Any, Dict, Iterable, List, Optional

from rich.console import Console
from rich.table import Table

from .bar_utils import build_red_green_bar
from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
)

# Reuse helpers from positions_panel so risk sees the same data/logic.
from backend.core.reporting_core.sonic_reporting.console_panels.positions_panel import (  # type: ignore
    _get_items_from_manager as _get_position_rows,
    _compute_travel_pct,
    _num,
    _to_mapping,
)

log = logging.getLogger(__name__)

PANEL_SLUG = "risk"
PANEL_NAME = "Risk Snapshot"

# 4x the original 10-segment bar → 40 segments total (4 per 10%)
BAR_SEGMENTS = 40
LABEL_COLOR = "cyan"

try:
    # Width hint for Rich export; theming already uses this
    from .theming import HR_WIDTH  # type: ignore
except Exception:  # pragma: no cover
    HR_WIDTH = 100


# ──────────────────────────────────────────────────────────────────────────────
# Aggregation
# ──────────────────────────────────────────────────────────────────────────────


def _compute_risk_metrics(items: Iterable[Any]) -> Dict[str, Optional[float]]:
    """
    Aggregate per-position fields into panel-level metrics.

    - Total Heat = size-weighted avg of heat_index (or current_heat_index)
    - Total Leverage / Travel = size-weighted averages
    - Balance uses size + position_type to split long vs short
    """
    total_weight = 0.0
    heat_num = 0.0
    trav_num = 0.0
    lev_num = 0.0
    long_notional = 0.0
    short_notional = 0.0

    for it in items:
        row = _to_mapping(it)
        size = _num(row.get("size"))
        if size is None:
            continue

        w = abs(size)
        if w == 0:
            continue

        total_weight += w

        # Heat: canonical risk metric from positions (heat_index / current_heat_index)
        heat_idx = _num(row.get("heat_index") or row.get("current_heat_index"))
        if heat_idx is not None:
            heat_num += w * heat_idx

        # Travel + leverage
        travel_pct = _compute_travel_pct(row)
        if travel_pct is not None:
            trav_num += w * travel_pct

        lev = _num(row.get("leverage"))
        if lev is not None:
            lev_num += w * lev

        # Long / short split for the balance bar
        ptype = (row.get("position_type") or row.get("side") or "").upper()
        if ptype == "LONG":
            long_notional += w
        elif ptype == "SHORT":
            short_notional += w
        else:
            # Fallback: infer from sign
            if size > 0:
                long_notional += w
            elif size < 0:
                short_notional += w

    def _safe(num: float, den: float) -> Optional[float]:
        return num / den if den and den != 0.0 else None

    return {
        "total_heat": _safe(heat_num, total_weight),
        "total_travel_pct": _safe(trav_num, total_weight),
        "total_leverage": _safe(lev_num, total_weight),
        "long_notional": long_notional,
        "short_notional": short_notional,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────


def _fmt_heat(v: Optional[float]) -> str:
    # Heat index is a scalar, not a percentage
    return f"{v:.2f}" if isinstance(v, (int, float)) else "—"


def _fmt_pct(v: Optional[float]) -> str:
    return f"{v:.2f}%" if isinstance(v, (int, float)) else "—"


def _fmt_lev(v: Optional[float]) -> str:
    return f"{v:.2f}×" if isinstance(v, (int, float)) else "—"


def _fmt_notional(v: Optional[float]) -> str:
    if not isinstance(v, (int, float)):
        return "—"
    return f"{v:.2f}"


def _label(text: str) -> str:
    return f"[{LABEL_COLOR}]{text}[/]"


def _build_balance_bar(
    short_notional: float,
    long_notional: float,
) -> tuple[str, str, str]:
    """
    Build SHORT/LONG balance bar and labels.

      SHORT ████▰▰▰ ... LONG
             (40 total segments, 4 per 10%)
    """
    total = short_notional + long_notional
    if total <= 0:
        bar = "[dim]────────────────────────────────────────[/dim]"
        bar_line = f"[red]SHORT[/red] {bar} [green]LONG[/green]"
        return bar_line, "—", "—"

    short_ratio = short_notional / total
    long_ratio = long_notional / total

    short_pct_txt = f"{short_ratio * 100:.0f}%"
    long_pct_txt = f"{long_ratio * 100:.0f}%"

    bar_line = build_red_green_bar(
        "[red]SHORT[/red]",
        "[green]LONG[/green]",
        short_ratio,
        slots=BAR_SEGMENTS,
    )
    return bar_line, short_pct_txt, long_pct_txt


def _build_pct_line(short_pct_txt: str, long_pct_txt: str) -> str:
    """
    Place the short/long percentages roughly under the red/green halves of the bar.

    We assume the bar line looks like: 'SHORT ' + BAR + ' LONG'
    so: 6 + BAR_SEGMENTS + 5 visible characters.
    """
    total_chars = 6 + BAR_SEGMENTS + 5  # 'SHORT ' + bar + ' LONG'
    line_chars = [" "] * total_chars

    short_label = f"{short_pct_txt} short"
    long_label = f"{long_pct_txt} long"

    # Center short under left half of bar
    short_center = 6 + BAR_SEGMENTS // 4
    short_start = max(0, min(total_chars - len(short_label), short_center - len(short_label) // 2))

    # Center long under right half of bar
    long_center = 6 + (3 * BAR_SEGMENTS) // 4
    long_start = max(0, min(total_chars - len(long_label), long_center - len(long_label) // 2))

    for i, ch in enumerate(short_label):
        line_chars[short_start + i] = ch
    for i, ch in enumerate(long_label):
        line_chars[long_start + i] = ch

    return "".join(line_chars).rstrip()


def _build_rich_block(metrics: Dict[str, Optional[float]]) -> List[str]:
    """
    Build the full block using Rich and export as plain text lines.

    Metrics and Long/Short/Total are on the same lines (4-column table),
    then the balance bar sits underneath.
    """
    buf = StringIO()
    console = Console(
        record=True,
        width=HR_WIDTH,
        file=buf,
        force_terminal=True,
    )

    long_sz = float(metrics.get("long_notional") or 0.0)
    short_sz = float(metrics.get("short_notional") or 0.0)
    total_sz = long_sz + short_sz

    # ── metrics + size table ──
    table = Table(
        show_header=False,
        box=None,
        pad_edge=False,
        expand=False,
        padding=(0, 2),  # a little extra space between columns
    )
    # metric label / metric value / size label / size value
    table.add_column(justify="left", no_wrap=True, ratio=2)
    table.add_column(justify="right", no_wrap=True, ratio=1)
    table.add_column(justify="left", no_wrap=True, ratio=2)
    table.add_column(justify="right", no_wrap=True, ratio=1)

    table.add_row(
        _label("🔥 Total Heat"),
        _fmt_heat(metrics.get("total_heat")),
        _label("Long"),
        _fmt_notional(long_sz),
    )
    table.add_row(
        _label("🔧 Total Leverage"),
        _fmt_lev(metrics.get("total_leverage")),
        _label("Short"),
        _fmt_notional(short_sz),
    )
    table.add_row(
        _label("🧭 Total Travel"),
        _fmt_pct(metrics.get("total_travel_pct")),
        _label("Total"),
        _fmt_notional(total_sz),
    )

    console.print(table)

    # ── balance bar + percentages ──
    bar_line, short_pct_txt, long_pct_txt = _build_balance_bar(
        short_notional=short_sz,
        long_notional=long_sz,
    )

    console.print()  # spacer
    console.print(bar_line)
    pct_line = _build_pct_line(short_pct_txt, long_pct_txt)
    console.print(pct_line)

    text = console.export_text(styles=True).rstrip("\n")
    return text.splitlines() if text else []


# ──────────────────────────────────────────────────────────────────────────────
# Public render / connector
# ──────────────────────────────────────────────────────────────────────────────


def render(context: Any, width: Optional[int] = None) -> List[str]:
    """
    Main entrypoint when called as render(ctx, width=…).

    Returns a list of pre-colored lines ready for console_reporter to print.
    """
    body_cfg = get_panel_body_config(PANEL_SLUG)
    lines: List[str] = []

    # Title rail (rounded box etc., via shared theming)
    lines += emit_title_block(PANEL_SLUG, PANEL_NAME)

    # Pull live positions via positions_panel helper
    try:
        items = _get_position_rows(context or {})
    except Exception:
        log.exception("risk_panel: failed to fetch positions; showing empty state")
        items = []

    if not items:
        msg = "(no positions available for risk summary)"
        msg_colored = color_if_plain(msg, body_cfg.get("body_text_color", "default"))
        lines += body_indent_lines(PANEL_SLUG, [msg_colored])
        lines += body_pad_below(PANEL_SLUG)
        return lines

    metrics = _compute_risk_metrics(items)
    block_lines = _build_rich_block(metrics)

    # Apply body color to plain lines, but don't override our ANSI-colored content.
    for raw in block_lines:
        lines += body_indent_lines(
            PANEL_SLUG,
            [color_if_plain(raw, body_cfg.get("body_text_color", "default"))],
        )

    lines += body_pad_below(PANEL_SLUG)
    return lines


def connector(
    dl: Any = None,
    ctx: Optional[Dict[str, Any]] = None,
    width: Optional[int] = None,
) -> List[str]:
    """
    console_reporter prefers connector(dl, ctx, width); delegate into render().
    """
    context: Dict[str, Any] = dict(ctx or {})
    if dl is not None:
        context.setdefault("dl", dl)
    if width is not None:
        context.setdefault("width", width)
    return render(context, width=width)
