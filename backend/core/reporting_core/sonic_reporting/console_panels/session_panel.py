# backend/core/reporting_core/sonic_reporting/console_panels/session_panel.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from io import StringIO

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

try:
    # Width hint for Rich export; theming already uses this
    from .theming import HR_WIDTH  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    HR_WIDTH = 100

PANEL_SLUG = "session"
PANEL_NAME = "Session / Goals"

# Time windows (in hours) – "All" is handled separately
_TIME_WINDOWS: List[Tuple[str, Optional[int]]] = [
    ("1h", 1),
    ("6h", 6),
    ("12h", 12),
    ("All", None),
]


# ───────────────────────────────── helpers ──────────────────────────────────


def _resolve_dl(context: Any) -> Any:
    """Get DataLocker from context (or return None)."""
    if isinstance(context, dict):
        dl = context.get("dl")
        if dl is not None:
            return dl
    return context if hasattr(context, "session") else None


def _parse_iso(ts: Any) -> Optional[datetime]:
    if ts is None:
        return None
    try:
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts))
        if isinstance(ts, str):
            return datetime.fromisoformat(ts)
    except Exception:
        return None
    return None


def _fmt_money(v: Optional[float]) -> str:
    return f"${v:,.2f}" if isinstance(v, (int, float)) else "—"


def _fmt_pct(v: Optional[float]) -> str:
    return f"{v:.2f}%" if isinstance(v, (int, float)) else "—"


def _trend_cell(delta: Optional[float], is_percent: bool = False) -> str:
    """Return a Rich-styled trend cell with ▲/▼ and color."""
    if not isinstance(delta, (int, float)):
        return "—"
    if abs(delta) < 1e-9:
        # flat
        return f"{0.00:.2f}%" if is_percent else _fmt_money(0.0)

    arrow = "▲" if delta > 0 else "▼"
    color = "green" if delta > 0 else "red"
    mag = abs(delta)
    if is_percent:
        return f"[{color}]{arrow} {mag:.2f}%[/]"
    return f"[{color}]{arrow} {_fmt_money(mag)}[/]"


def _compute_timeframe_deltas(
    dl: Any,
) -> Tuple[Optional[float], Dict[str, Dict[str, Optional[float]]]]:
    """
    Compute All-time and per-window deltas from portfolio snapshots.

    Returns:
      (session_start_value, {
        "1h": {"delta": float|None, "pct": float|None},
        "6h": {...},
        "12h": {...},
        "All": {...},
      })
    """
    mgr = getattr(dl, "portfolio", None)
    if mgr is None or not hasattr(mgr, "get_snapshots"):
        return None, {}

    try:
        snaps = mgr.get_snapshots()
    except Exception:
        snaps = []

    if not snaps:
        return None, {}

    # Assume DLPortfolioManager.get_snapshots returns ascending by snapshot_time
    # (see dl_portfolio.py). We treat the latest snapshot as "now".
    last = snaps[-1]
    last_ts = _parse_iso(getattr(last, "snapshot_time", None))
    if last_ts is None:
        last_ts = datetime.now()

    try:
        start_val = float(getattr(last, "session_start_value", 0.0) or 0.0)
    except Exception:
        start_val = 0.0
    try:
        all_delta = float(getattr(last, "current_session_value", 0.0) or 0.0)
    except Exception:
        all_delta = 0.0

    def _safe_curr(snap: Any) -> float:
        try:
            return float(getattr(snap, "current_session_value", 0.0) or 0.0)
        except Exception:
            return 0.0

    # Precompute times for all snapshots (ascending)
    ts_list: List[Tuple[datetime, Any]] = []
    for s in snaps:
        ts = _parse_iso(getattr(s, "snapshot_time", None))
        if ts is not None:
            ts_list.append((ts, s))

    if not ts_list:
        return start_val, {}

    metrics: Dict[str, Dict[str, Optional[float]]] = {}

    # All-time (since session start)
    pct_all = None
    if start_val > 0:
        pct_all = all_delta / start_val * 100.0
    metrics["All"] = {"delta": all_delta, "pct": pct_all}

    # Sliding windows
    for label, hours in _TIME_WINDOWS:
        if hours is None:
            # already handled as "All"
            continue

        cutoff = last_ts - timedelta(hours=hours)

        baseline = None
        # walk snapshots backwards until we find one within the window
        for ts, snap in reversed(ts_list):
            if ts <= last_ts and ts >= cutoff:
                baseline = _safe_curr(snap)
                break

        if baseline is None:
            metrics[label] = {"delta": None, "pct": None}
            continue

        delta_val = all_delta - baseline
        pct_val = None
        if start_val > 0:
            pct_val = delta_val / start_val * 100.0
        metrics[label] = {"delta": delta_val, "pct": pct_val}

    return start_val, metrics


# ────────────────────────────────── Rich table plumbing ─────────────────────


def _resolve_table_cfg(body_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve Rich table settings for the Session panel (defaults to thin)."""
    tcfg = (body_cfg or {}).get("table") or {}
    style = str(tcfg.get("style") or "").lower().strip() or "thin"
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
    """Apply table-level justification to rendered text lines."""
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


def _is_rule_line(line: str) -> bool:
    """Return True if a line is just box-drawing/horizontal rule characters."""
    stripped = line.strip()
    if not stripped:
        return False
    chars = set(stripped)
    rule_chars = set("┌┐└┘├┤┬┴┼─━═╭╮╯╰╴╶╷╵╸╹╺╻╼╽╾╿+|")
    return chars <= rule_chars


def _build_perf_table(
    metrics: Dict[str, Dict[str, Optional[float]]],
    body_cfg: Dict[str, Any],
) -> List[str]:
    """
    Build a Rich table representing session performance by timeframe and
    export as text.

    Columns: Metric × (1h, 6h, 12h, All-time)
    Rows:    Δ $, Δ %
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

    # Header labels with icons
    table.add_column("📏 Metric", justify="left", no_wrap=True)
    table.add_column("⏱ 1h", justify="right", no_wrap=True)
    table.add_column("🕓 6h", justify="right", no_wrap=True)
    table.add_column("🕕 12h", justify="right", no_wrap=True)
    table.add_column("📈 All-time", justify="right", no_wrap=True)

    # Rows: Δ $ and Δ %
    labels = ["💵 Δ $", "📈 Δ %"]
    for row_idx, metric_label in enumerate(labels):
        cells: List[str] = [metric_label]
        for label, hours in _TIME_WINDOWS:
            cell_metrics = metrics.get(label, {})
            if row_idx == 0:
                delta_val = cell_metrics.get("delta")
                cells.append(_trend_cell(delta_val, is_percent=False))
            else:
                pct_val = cell_metrics.get("pct")
                cells.append(_trend_cell(pct_val, is_percent=True))
        table.add_row(*cells)

    buf = StringIO()
    console = Console(record=True, width=HR_WIDTH, file=buf, force_terminal=True)
    console.print(table)
    # Preserve Rich color/style markup so trend arrows keep their colors.
    text = console.export_text(styles=True).rstrip("\n")
    if not text:
        return []

    raw_lines = text.splitlines()
    # Remove pure rule lines (header underline, borders, if any)
    cleaned = [ln for ln in raw_lines if not _is_rule_line(ln)]
    return _justify_lines(cleaned, table_cfg["table_justify"], HR_WIDTH)


# ─────────────────────────────────── render ─────────────────────────────────


def render(context: Any, width: Optional[int] = None) -> List[str]:
    """
    Accepted:
      render(ctx)
      render(dl, ctx)
      render(ctx, width)
    Returns a list of lines; console_reporter will print them.
    """
    # Normalize context to always have a dict with dl + cfg
    ctx: Dict[str, Any] = {}
    if isinstance(context, dict):
        ctx.update(context)
    else:
        ctx["dl"] = context

    dl = _resolve_dl(ctx)
    body_cfg = get_panel_body_config(PANEL_SLUG)

    lines: List[str] = []
    lines.extend(emit_title_block(PANEL_SLUG, PANEL_NAME))

    if dl is None or not hasattr(dl, "session"):
        # No DataLocker or no session manager – graceful degrade
        msg = "Session manager unavailable. Use LaunchPad #14 (Session / Goals Console) to configure."
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [color_if_plain(msg, body_cfg.get("body_text_color", ""))],
            )
        )
        lines.extend(body_pad_below(PANEL_SLUG))
        return lines

    session_mgr = dl.session
    active = None
    try:
        active = session_mgr.get_active_session()
    except Exception:
        active = None

    if active is None:
        msg = "No active session. Use LaunchPad #14 (Session / Goals Console) to start one."
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [color_if_plain(msg, body_cfg.get("body_text_color", ""))],
            )
        )
        lines.extend(body_pad_below(PANEL_SLUG))
        return lines

    # --- Status + label block ------------------------------------------------
    status_raw = getattr(active, "status", "OPEN") or "OPEN"
    status_norm = str(status_raw).upper()
    status_icon = "🟢" if status_norm == "OPEN" else "⚪"
    session_label = getattr(active, "session_label", None)
    goal_mode = getattr(active, "goal_mode", None)

    # Start time / start value / goal
    start_ts = getattr(active, "session_start_time", None)
    start_str = ""
    if start_ts is not None:
        try:
            if isinstance(start_ts, str):
                start_str = start_ts
            else:
                start_str = start_ts.isoformat(timespec="seconds")
        except Exception:
            start_str = str(start_ts)

    start_val = getattr(active, "session_start_value", 0.0)
    goal_val = getattr(active, "session_goal_value", 0.0)
    curr_val = getattr(active, "current_session_value", 0.0)
    perf_val = getattr(active, "session_performance_value", 0.0)
    notes = getattr(active, "notes", None)

    status_line = f"  🧭 Status: {status_icon} {status_norm}"
    if session_label:
        mode_tag = f" ({goal_mode})" if goal_mode else ""
        status_line += f"   🎟 Label: {session_label}{mode_tag}"

    start_line = f"  🕒 Start: {start_str or 'unknown'}   💰 Start $: {_fmt_money(start_val)}"

    # Goal line + All-time summary
    goal_line = f"  🎯 Goal: {_fmt_money(goal_val)}"
    all_label = "All"
    start_for_pct, metrics = _compute_timeframe_deltas(dl)
    all_metrics = metrics.get(all_label, {}) if metrics else {}
    all_delta = all_metrics.get("delta", curr_val)
    all_pct = all_metrics.get("pct")
    # Fall back on performance_value for All-time delta if metrics empty
    if not isinstance(all_delta, (int, float)):
        all_delta = perf_val
    all_trend_val = _trend_cell(all_delta, is_percent=False)
    all_trend_pct = _trend_cell(all_pct, is_percent=True) if all_pct is not None else ""

    if all_trend_pct:
        goal_line += f"   📈 All-time: {all_trend_val}  ({all_trend_pct})"
    else:
        goal_line += f"   📈 All-time: {all_trend_val}"

    lines.extend(
        body_indent_lines(
            PANEL_SLUG,
            [
                color_if_plain(status_line, body_cfg.get("body_text_color", "")),
                color_if_plain(start_line, body_cfg.get("body_text_color", "")),
                color_if_plain(goal_line, body_cfg.get("body_text_color", "")),
            ],
        )
    )
    lines.append("")

    # --- Performance table ---------------------------------------------------
    if not metrics:
        msg = "No portfolio snapshots yet. Run Cyclone / Positions to populate session performance."
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [color_if_plain(msg, body_cfg.get("body_text_color", ""))],
            )
        )
        lines.extend(body_pad_below(PANEL_SLUG))
        return lines

    table_lines = _build_perf_table(metrics, body_cfg)

    if table_lines:
        header_line = table_lines[0]
        data_lines = table_lines[1:]

        # Header tinted like other panels
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [paint_line(header_line, body_cfg.get("column_header_text_color", ""))],
            )
        )
        # Body uses normal body_text_color (and respects inline markup)
        for ln in data_lines:
            lines.extend(
                body_indent_lines(
                    PANEL_SLUG,
                    [color_if_plain(ln, body_cfg.get("body_text_color", ""))],
                )
            )

    # Optional notes line
    if notes:
        lines.append("")
        note_line = f"  📝 Notes: {notes}"
        lines.extend(
            body_indent_lines(
                PANEL_SLUG,
                [color_if_plain(note_line, body_cfg.get("body_text_color", ""))],
            )
        )

    lines.extend(body_pad_below(PANEL_SLUG))
    return lines


def connector(*args, **kwargs) -> List[str]:
    """console_reporter prefers connector(); delegate to render()."""
    return render(*args, **kwargs)
