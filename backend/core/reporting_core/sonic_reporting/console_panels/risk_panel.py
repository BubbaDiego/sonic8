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
        return bar, "—", "—"

    short_ratio = short_notional / total
    long_ratio = long_notional / total

    short_pct_txt = f"{short_ratio * 100:.0f}%"
    long_pct_txt = f"{long_ratio * 100:.0f}%"

    short_blocks = int(round(short_ratio * BAR_SEGMENTS))
    short_blocks = max(0, min(short_blocks, BAR_SEGMENTS))
    long_blocks = BAR_SEGMENTS - short_blocks

    short_seg = "[red]" + ("▰" * short_blocks) + "[/red]" if short_blocks else ""
    long_seg = "[green]" + ("▰" * long_blocks) + "[/green]" if long_blocks else ""

    if not short_seg and not long_seg:
        long_seg = "[green]▰[/green]"

    bar = short_seg + long_seg
    return bar, short_pct_txt, long_pct_txt


def _build_rich_block(metrics: Dict[str, Optional[float]]) -> List[str]:
    """
    Build the full block using Rich and export as plain text lines.

    We let Rich handle **all** markup (metrics + bar) and then export ANSI text,
    so no `[red]...[/red]` leaks through.
    """
    buf = StringIO()
    console = Console(
        record=True,
        width=HR_WIDTH,
        file=buf,
        force_terminal=True,
    )

    # ── metrics + size table ──
    table = Table(
        show_header=False,
        box=None,
        pad_edge=False,
        expand=False,
    )
    table.add_column(justify="left", no_wrap=True)
    table.add_column(justify="right", no_wrap=True)

    table.add_row("🔥 Total Heat", _fmt_heat(metrics.get("total_heat")))
    table.add_row("🔧 Total Leverage", _fmt_lev(metrics.get("total_leverage")))
    table.add_row("🧭 Total Travel", _fmt_pct(metrics.get("total_travel_pct")))

    long_sz = float(metrics.get("long_notional") or 0.0)
    short_sz = float(metrics.get("short_notional") or 0.0)
    total_sz = long_sz + short_sz

    table.add_row("", "")
    table.add_row("Long", _fmt_notional(long_sz))
    table.add_row("Short", _fmt_notional(short_sz))
    table.add_row("Total", _fmt_notional(total_sz))

    console.print(table)

    # ── balance bar + percentages ──
    bar, short_pct_txt, long_pct_txt = _build_balance_bar(
        short_notional=short_sz,
        long_notional=long_sz,
    )

    console.print()  # spacer
    # Bar line: bar sits directly after SHORT
    console.print(f"[red]SHORT[/red] {bar} [green]LONG[/green]")
    # Percent line: numbers closer to labels (no huge right-justified gap)
    console.print(f"{short_pct_txt} short   {long_pct_txt} long")

    # Export all content (metrics + bar) with ANSI styles preserved
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
