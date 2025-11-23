from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.data.data_locker import DataLocker
from backend.core.session_core.session_core import SessionCore
from backend.core.session_core.session_models import SessionPerformance, SessionStatus
from .theming import console_width


def _panel_to_lines(panel: Panel, width: Optional[int] = None) -> List[str]:
    console = Console(width=width or console_width(), record=True)
    console.print(panel)
    return console.export_text(clear=False).splitlines()


def _format_money(value: Optional[float]) -> str:
    if value is None:
        return "—"
    try:
        return f"{value:,.2f}"
    except Exception:
        return str(value)


def _format_pct(value: Optional[float]) -> str:
    if value is None:
        return "—"
    try:
        return f"{value:+.2f}%"
    except Exception:
        return str(value)


def _status_icon(status: SessionStatus) -> str:
    try:
        value = status.value
    except Exception:
        value = str(status)
    return {
        "active": "[green]●[/]",
        "paused": "[yellow]●[/]",
        "closed": "[dim]●[/]",
    }.get(value, "[dim]○[/]")


def _format_window(start: Optional[datetime], end: Optional[datetime]) -> str:
    if not start or not end:
        return "—"
    try:
        return f"{start.isoformat(timespec='minutes')} → {end.isoformat(timespec='minutes')}"
    except Exception:
        return f"{start} → {end}"


def build_sessions_panel(dl: DataLocker, width: Optional[int] = None) -> Panel:
    core = SessionCore(dl)
    sessions = core.list_sessions(active_only=False, enabled_only=True)

    # Active sessions first, then newest by created_at
    def _sort_key(session):
        created = session.created_at if isinstance(session.created_at, datetime) else None
        ts = created.timestamp() if created else 0.0
        return (0 if session.status is SessionStatus.ACTIVE else 1, -ts)

    sessions = sorted(sessions, key=_sort_key)

    if not sessions:
        return Panel(
            "No sessions configured. Create sessions via the SessionCore Console (Launch Pad → 16).",
            title="🎯 Sessions Overview",
            border_style="cyan",
        )

    table = Table(box=box.SIMPLE_HEAVY, show_lines=False)
    table.add_column("#", style="dim", justify="right", width=3)
    table.add_column("Session")
    table.add_column("Wallet", style="dim")
    table.add_column("PnL", justify="right")
    table.add_column("Return %", justify="right")
    table.add_column("Max DD %", justify="right")
    table.add_column("Samples", justify="right", style="dim")
    table.add_column("Window", style="dim")

    for idx, session in enumerate(sessions, start=1):
        perf: Optional[SessionPerformance] = core.safe_get_performance(session.sid)

        pnl = perf.pnl if perf else None
        pnl_color = "dim" if pnl is None or pnl == 0 else ("green" if pnl > 0 else "red")
        return_pct = perf.return_pct if perf else None
        return_color = "dim" if return_pct is None or return_pct == 0 else ("green" if return_pct > 0 else "red")
        max_dd = perf.max_drawdown_pct if perf else None
        samples = perf.samples if perf else 0
        window = _format_window(
            perf.start if perf else session.created_at if isinstance(session.created_at, datetime) else None,
            perf.end if perf else session.closed_at if isinstance(session.closed_at, datetime) else None,
        )

        table.add_row(
            str(idx),
            f"{_status_icon(session.status)} {session.name}",
            session.primary_wallet_name,
            f"[{pnl_color}]{_format_money(pnl)}[/]",
            f"[{return_color}]{_format_pct(return_pct)}[/]",
            _format_pct(max_dd),
            str(samples),
            window,
        )

    return Panel(
        table,
        title=f"🎯 Sessions Overview ({len(sessions)} enabled)",
        border_style="cyan",
    )


def connector(dl: Optional[DataLocker] = None, ctx: Optional[Dict[str, Any]] = None, width: Optional[int] = None) -> List[str]:
    context = dict(ctx or {})
    if dl is None:
        dl = context.get("dl") or DataLocker.get_instance()
    panel = build_sessions_panel(dl, width=width)
    return _panel_to_lines(panel, width=width)


__all__ = [
    "build_sessions_panel",
    "connector",
]
