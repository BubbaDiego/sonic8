from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional

from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


TITLE = "🎯 Session / Goals"


# ───────────────────────── helpers ───────────────────────── #


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Safe field accessor for dicts, Pydantic models, and plain objects."""
    if obj is None:
        return default

    if isinstance(obj, Mapping):
        return obj.get(key, default)

    # Pydantic BaseModel / dataclasses / simple objects
    return getattr(obj, key, default)


def _parse_dt(value: Any) -> Optional[datetime]:
    """Parse a datetime from Session fields (datetime or ISO string)."""
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        s = value.strip()
        # tolerate trailing "Z"
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    return None


def _fmt_timestamp(value: Any) -> str:
    """
    Format session_start_time as: 11/17/25 8:15PM
    (MM/DD/YY, 12-hour clock, no leading zero on hour).
    """
    dt = _parse_dt(value)
    if not dt:
        return "—"
    date_part = dt.strftime("%m/%d/%y")
    time_part = dt.strftime("%I:%M%p").lstrip("0")  # 08:15PM → 8:15PM
    return f"{date_part} {time_part}"


def _fmt_money(value: Any) -> str:
    """Format a value as $1,234.56 or '—'."""
    if value is None:
        return "—"
    try:
        v = float(value)
    except Exception:
        return str(value)
    return f"${v:,.2f}"


def _fmt_delta_money(delta: Any) -> Text:
    """
    Render a P&L delta as colored arrow + dollars, e.g.:

        ▲ $89.11  (green)
        ▼ $12.34  (red)
    """
    if delta is None:
        return Text("—", style="dim")

    try:
        v = float(delta)
    except Exception:
        # if something weird comes through, at least show it
        return Text(str(delta))

    is_up = v >= 0
    arrow = "▲" if is_up else "▼"
    style = "green" if is_up else "red"
    body = _fmt_money(abs(v))
    return Text(f"{arrow} {body}", style=style)


def _fmt_delta_pct(delta_pct: Any) -> Text:
    """Same idea as _fmt_delta_money but for percentages."""
    if delta_pct is None:
        return Text("—", style="dim")

    try:
        v = float(delta_pct)
    except Exception:
        return Text(str(delta_pct))

    is_up = v >= 0
    arrow = "▲" if is_up else "▼"
    style = "green" if is_up else "red"
    return Text(f"{arrow} {abs(v):,.2f}%", style=style)


def _horizon_cell(
    perf: Mapping[str, Any],
    key: str,
) -> tuple[Text, Text]:
    """
    perf is expected to look like:

        {
          "1h":  {"delta_usd": 0.0, "delta_pct": 0.0},
          "6h":  {...},
          "12h": {...},
          "all": {...},
        }
    """
    horizon = perf.get(key) or {}
    dv = horizon.get("delta_usd")
    dp = horizon.get("delta_pct")

    if dv is None:
        dv_text = Text("$0.00", style="dim")
    else:
        dv_text = _fmt_delta_money(dv)

    if dp is None:
        dp_text = Text("—", style="dim")
    else:
        dp_text = _fmt_delta_pct(dp)

    return dv_text, dp_text


# ───────────────────────── main render ───────────────────────── #


def build_session_panel(
    session: Any | None,
    perf: Mapping[str, Mapping[str, Any]] | None = None,
) -> Panel:
    """
    Build the 🎯 Session / Goals Rich panel.

    Parameters
    ----------
    session
        A `backend.models.session.Session` instance, a dict with the same
        fields, or `None` if no active session.
    perf
        Optional per-horizon performance:

            {
              "1h":  {"delta_usd": float, "delta_pct": float},
              "6h":  {...},
              "12h": {...},
              "all": {...},
            }

    Returns
    -------
    Panel
        Rich Panel ready to plug into the console UI layout.
    """
    perf = perf or {}

    if session is None:
        msg = Text(
            "No active session.\n\n"
            "Use the Session / Goals menu to start one.",
            style="yellow",
        )
        return Panel(
            Align.left(msg),
            title=TITLE,
            border_style="white",
            padding=(1, 2),
        )

    # --- core fields from Session model ------------------------------------- #
    status = str(_get(session, "status", "OPEN") or "").upper()
    label = _get(session, "label")  # optional, not part of Session model
    goal_mode = (
        _get(session, "goal_mode")
        or _get(session, "mode")
        or _get(session, "goal_mode_name")
    )

    start_time = _get(session, "session_start_time")
    start_value = _get(session, "session_start_value")
    goal_value = _get(session, "session_goal_value")
    current_value = _get(session, "current_session_value")

    # Prefer explicit session_performance_value, otherwise derive from current/start
    perf_value = _get(session, "session_performance_value")
    if perf_value is None and start_value is not None and current_value is not None:
        try:
            perf_value = float(current_value) - float(start_value)
        except Exception:
            perf_value = None

    # --- header line -------------------------------------------------------- #
    status_dot = "🟢" if status == "OPEN" else "🔴"
    header = Text()

    header.append(status_dot + " ", style="green" if status == "OPEN" else "red")
    header.append(status)

    if label is not None:
        header.append("  •  ")
        header.append(f"Label {label}")

    if goal_mode:
        header.append(" (")
        header.append(str(goal_mode))
        header.append(")")

    header.append("  •  ")
    header.append(_fmt_timestamp(start_time))

    # --- summary block: Start / Current / Goal / All-time Δ ----------------- #
    summary = Table.grid(padding=(0, 1))
    summary.add_row(header)

    row1 = Text("Start   : ")
    row1.append(_fmt_money(start_value))
    row1.append("      All-time Δ: ")
    row1.append(_fmt_delta_money(perf_value))
    summary.add_row(row1)

    row2 = Text("Current : ")
    row2.append(Text(_fmt_money(current_value), style="cyan"))
    row2.append("      Goal      : ")
    row2.append(_fmt_money(goal_value))
    summary.add_row(row2)

    # --- horizon table (1h / 6h / 12h / All-time) --------------------------- #
    d1h, p1h = _horizon_cell(perf, "1h")
    d6h, p6h = _horizon_cell(perf, "6h")
    d12h, p12h = _horizon_cell(perf, "12h")
    dall, pall = _horizon_cell(perf, "all")

    table = Table.grid(padding=(0, 3))
    table.add_row(
        Text("📊 Metric"),
        Text("⏱ 1h"),
        Text("⏱ 6h"),
        Text("⏱ 12h"),
        Text("📅 All-time"),
    )
    table.add_row("💵 Δ $", d1h, d6h, d12h, _fmt_delta_money(perf_value))
    table.add_row("📈 Δ %", p1h, p6h, p12h, pall)

    # --- compose ------------------------------------------------------------ #
    body = Table.grid(padding=(0, 0))
    body.add_row(summary)
    body.add_row(Text())  # spacer
    body.add_row(table)

    return Panel(
        Align.left(body),
        title=TITLE,
        border_style="white",
        padding=(1, 2),
    )


# Convenience alias if other modules expect `render_session_panel`
render_session_panel = build_session_panel


if __name__ == "__main__":  # pragma: no cover - manual demo helper
    from rich.console import Console

    demo_session = {
        "status": "OPEN",
        "label": 15,
        "goal_mode": "GoalMode.DELTA",
        "session_start_time": datetime.utcnow().isoformat(),
        "session_start_value": 100.0,
        "current_session_value": 189.11,
        "session_goal_value": 200.0,
        "session_performance_value": 89.11,
    }
    demo_perf = {
        "1h": {"delta_usd": 0.0, "delta_pct": None},
        "6h": {"delta_usd": 0.0, "delta_pct": None},
        "12h": {"delta_usd": 0.0, "delta_pct": None},
        "all": {"delta_usd": 89.11, "delta_pct": 89.11},
    }

    console = Console()
    console.print(build_session_panel(demo_session, demo_perf))
