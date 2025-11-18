from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Tuple
from io import StringIO
import os

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from backend.core.reporting_core.sonic_reporting.console_panels import data_access

# Keep this roughly aligned with your other panels
try:
    _SESSION_DEFAULT_WIDTH = int(os.getenv("SONIC_CONSOLE_WIDTH", "92"))
except Exception:
    _SESSION_DEFAULT_WIDTH = 92

# Make Session / Goals feel like a “card”: a bit narrower than the full console,
# but never absurdly tiny.
SESSION_PANEL_WIDTH = max(60, min(_SESSION_DEFAULT_WIDTH - 10, _SESSION_DEFAULT_WIDTH))
TITLE = "🎯 Session / Goals"


# ───────────────────────── helpers ───────────────────────── #


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Safe field accessor for dicts / Pydantic models / simple objects."""
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None
    return None


def _fmt_timestamp(value: Any) -> str:
    """
    Format as: 11/17/25 8:36PM (MM/DD/YY, 12-hour, no leading zero on hour).
    """
    dt = _parse_dt(value)
    if not dt:
        return "—"
    date_part = dt.strftime("%m/%d/%y")
    time_part = dt.strftime("%I:%M%p").lstrip("0")
    return f"{date_part} {time_part}"


def _fmt_money(value: Any) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
    except Exception:
        return str(value)
    return f"${v:,.2f}"


def _fmt_delta_money(delta: Any) -> Text:
    """▲ / ▼ + colored dollars."""
    if delta is None:
        return Text("—", style="dim")
    try:
        v = float(delta)
    except Exception:
        return Text(str(delta))
    up = v >= 0
    arrow = "▲" if up else "▼"
    style = "green" if up else "red"
    body = _fmt_money(abs(v))
    return Text(f"{arrow} {body}", style=style)


def _fmt_delta_pct(delta_pct: Any) -> Text:
    if delta_pct is None:
        return Text("—", style="dim")
    try:
        v = float(delta_pct)
    except Exception:
        return Text(str(delta_pct))
    up = v >= 0
    arrow = "▲" if up else "▼"
    style = "green" if up else "red"
    # 🔧 FIX: use :,.2f (comma + 2 decimals) instead of invalid :,2f
    return Text(f"{arrow} {abs(v):,.2f}%", style=style)


def _horizon_cell(perf: Mapping[str, Any], key: str) -> Tuple[Text, Text]:
    """
    perf:
      {
        "1h":  {"delta_usd": 0.0, "delta_pct": 0.0},
        "6h":  {...},
        "12h": {...},
        "all": {...},
      }
    """
    block = perf.get(key) or {}
    dv = block.get("delta_usd")
    dp = block.get("delta_pct")

    dv_text = _fmt_delta_money(dv) if dv is not None else Text("$0.00", style="dim")
    dp_text = _fmt_delta_pct(dp) if dp is not None else Text("—", style="dim")
    return dv_text, dp_text


def _resolve_dl(context: Any) -> Any:
    """
    Best-effort resolver for a DataLocker instance from the given context.

    Accepts:
      - ctx dict with key 'dl'
      - direct DataLocker instance
      - anything supported by data_access.dl_or_context(...)
    """

    try:
        return data_access.dl_or_context(context)
    except Exception:
        # Fallback: try global DataLocker singleton
        try:
            from backend.data.data_locker import DataLocker  # type: ignore

            if hasattr(DataLocker, "get_instance"):
                return DataLocker.get_instance()  # type: ignore[call-arg]
            return DataLocker()  # type: ignore[call-arg]
        except Exception:
            return None


def _get_active_session(context: Any) -> Any:
    """
    Return the active DLSessionManager session, or None if unavailable.
    """

    dl = _resolve_dl(context)
    if dl is None:
        return None

    mgr = getattr(dl, "session", None)
    if mgr is None:
        return None

    try:
        return mgr.get_active_session()
    except Exception:
        return None


def _panel_to_lines(panel: Panel, width: Optional[int] = None) -> List[str]:
    """
    Render a Rich Panel to a list of text lines (with ANSI styles preserved),
    suitable for console_reporter.render_panel_stack().
    """

    buf = StringIO()
    console = Console(
        record=True,
        width=int(width or SESSION_PANEL_WIDTH),
        file=buf,
        force_terminal=True,
    )
    console.print(panel)

    text = console.export_text(styles=True).rstrip("\n")
    if not text:
        return []

    lines = text.splitlines()

    # Trim leading/trailing blank lines so the stack stays tight
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    return lines


# ───────────────────────── main render ───────────────────────── #


def build_session_panel(
    session: Any | None,
    perf: Mapping[str, Mapping[str, Any]] | None = None,
) -> Panel:
    """
    Build the compact 🎯 Session / Goals panel.

    session: Session model or dict with fields like:
      - status
      - goal_mode / mode / goal_mode_name
      - session_start_time
      - session_start_value
      - current_session_value
      - session_goal_value
      - session_performance_value (optional; falls back to current - start)

    perf: optional horizon metrics:
      {
        "1h":  {"delta_usd": float, "delta_pct": float},
        "6h":  {...},
        "12h": {...},
        "all":  {...},
      }
    """
    perf = perf or {}

    # No active session → simple panel
    if session is None:
        msg = Text(
            "No active session.\n\n"
            "Use the Session / Goals menu to start one.",
            style="yellow",
        )
        return Panel(
            msg,
            title=TITLE,
            border_style="white",
            width=SESSION_PANEL_WIDTH,
            padding=(1, 2),
        )

    # Core fields
    status = str(_get(session, "status", "OPEN") or "").upper()
    goal_mode = (
        _get(session, "goal_mode")
        or _get(session, "mode")
        or _get(session, "goal_mode_name")
    )
    label = _get(session, "label")  # optional, may not exist

    start_time = _get(session, "session_start_time")
    start_val = _get(session, "session_start_value")
    goal_val = _get(session, "session_goal_value")
    curr_val = _get(session, "current_session_value")
    if curr_val is None:
        # some paths use current_total_value instead
        curr_val = _get(session, "current_total_value")

    perf_val = _get(session, "session_performance_value")
    if perf_val is None and start_val is not None and curr_val is not None:
        try:
            perf_val = float(curr_val) - float(start_val)
        except Exception:
            perf_val = None

    # Header line: 🟢 OPEN (GoalMode.DELTA) • 11/17/25 8:36PM • Label 15
    status_dot = "🟢" if status == "OPEN" else "🔴"
    header = Text()
    header.append(status_dot + " ", style="green" if status == "OPEN" else "red")
    header.append(status)
    if goal_mode:
        header.append(" (")
        header.append(str(goal_mode))
        header.append(")")
    header.append("  •  ")
    header.append(_fmt_timestamp(start_time))
    if label is not None:
        header.append("  •  ")
        header.append(f"Label {label}")

    # Summary block
    summary = Table.grid(padding=(0, 1))
    summary.add_row(header)

    row1 = Text("Start   : ")
    row1.append(_fmt_money(start_val))
    row1.append("      All-time Δ : ")
    row1.append(_fmt_delta_money(perf_val))
    summary.add_row(row1)

    row2 = Text("Current : ")
    row2.append(Text(_fmt_money(curr_val), style="cyan"))
    row2.append("      Goal       : ")
    row2.append(_fmt_money(goal_val))
    summary.add_row(row2)

    # Horizon table (1h / 6h / 12h / All-time)
    d1h, p1h = _horizon_cell(perf, "1h")
    d6h, p6h = _horizon_cell(perf, "6h")
    d12h, p12h = _horizon_cell(perf, "12h")
    dall, pall = _horizon_cell(perf, "all")

    horizon = Table.grid(padding=(0, 3))
    horizon.add_row(
        Text("📊 Metric"),
        Text("⏱ 1h"),
        Text("⏱ 6h"),
        Text("⏱ 12h"),
        Text("📅 All-time"),
    )
    horizon.add_row("💵 Δ $", d1h, d6h, d12h, _fmt_delta_money(perf_val))
    horizon.add_row("📈 Δ %", p1h, p6h, p12h, pall)

    # Combine into a single narrow grid
    outer = Table.grid(padding=0)
    outer.add_row(summary)
    outer.add_row(Text())  # spacer
    outer.add_row(horizon)

    return Panel(
        outer,
        title=TITLE,
        border_style="white",
        width=SESSION_PANEL_WIDTH,
        padding=(1, 2),
    )


def render(context: Any, width: Optional[int] = None) -> List[str]:
    """
    Main entrypoint when called as render(ctx, width=…).

    Accepted call shapes (matching other console_panels modules):
      - render(ctx)
      - render(dl, ctx)
      - render(ctx, width)

    Returns a list of text lines; console_reporter will print them.
    """

    # Normalize context to a dict with at least a dl entry when available
    if isinstance(context, dict):
        ctx: Dict[str, Any] = dict(context)
    else:
        ctx = {"dl": context}

    # Allow tests or callers to inject a session directly via ctx["session"];
    # otherwise, resolve the active session from DataLocker.
    session_obj = ctx.get("session")
    if session_obj is None:
        session_obj = _get_active_session(ctx)

    # Optional per-horizon performance can be provided via ctx["session_perf"].
    perf_obj = ctx.get("session_perf")
    perf: Mapping[str, Mapping[str, Any]]
    if isinstance(perf_obj, Mapping):
        perf = perf_obj  # type: ignore[assignment]
    else:
        perf = {}

    panel = build_session_panel(session_obj, perf)

    # Prefer explicit width from the caller or ctx, but never exceed
    # SESSION_PANEL_WIDTH so the block stays visually narrower than the
    # surrounding tables.
    base_width = width or ctx.get("width") or SESSION_PANEL_WIDTH
    try:
        base_width_int = int(base_width)
    except Exception:
        base_width_int = SESSION_PANEL_WIDTH

    effective_width = min(base_width_int, SESSION_PANEL_WIDTH)
    return _panel_to_lines(panel, width=effective_width)


def connector(
    dl: Any = None,
    ctx: Optional[Dict[str, Any]] = None,
    width: Optional[int] = None,
) -> List[str]:
    """
    console_reporter prefers connector(dl, ctx, width); delegate into render().

    This matches the connector(...) pattern used by other panels so
    console_reporter.render_panel_stack() will pick us up automatically.
    """

    context: Dict[str, Any] = dict(ctx or {})
    if dl is not None:
        context.setdefault("dl", dl)
    if width is not None:
        context.setdefault("width", width)
    return render(context, width=width)


# Backwards-compat aliases so the layout can call whatever it wants
render_session_panel = build_session_panel
render_panel = build_session_panel

__all__ = [
    "build_session_panel",
    "render_session_panel",
    "render_panel",
    "render",
    "connector",
]
