"""Live cycle activity table rendered with Rich."""

from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


_STATUS_LABELS = {
    "pending": "pending",
    "running": "running",
    "success": "success",
    "warn": "warn",
    "fail": "fail",
}

_STATUS_STYLES = {
    "pending": "dim",
    "running": "cyan",
    "success": "green",
    "warn": "yellow",
    "fail": "red",
}

_SUMMARY_STYLES = {
    "success": "bold green",
    "warn": "bold yellow",
    "fail": "bold red",
}


class CycleActivityStream:
    """Render :class:`ActivityLogger` events as a live Rich table."""

    def __init__(self, console: Console, refresh_hz: float = 10.0) -> None:
        self.console = console
        self.refresh_hz = float(refresh_hz) if refresh_hz and refresh_hz > 0 else 10.0

        self._activities: Dict[int, Dict[str, Any]] = {}
        self._order: List[int] = []
        self._cycle_id: Optional[int] = None
        self._cycle_started_at: Optional[float] = None
        self._cycle_ended_at: Optional[float] = None
        self._live: Optional[Live] = None
        self._last_render: float = 0.0
        self._pending_events: List[Tuple[str, Dict[str, Any]]] = []

    # ------------------------------------------------------------------ API
    def begin(self, cycle_id: int) -> None:
        """Start rendering a new cycle."""

        self._cycle_id = cycle_id
        self._cycle_started_at = time.time()
        self._cycle_ended_at = None
        self._activities.clear()
        self._order.clear()

        self._start_live()
        self._refresh(force=True)

    def on_event(self, event: str, payload: Dict[str, Any]) -> None:
        """Mirror :class:`ActivityLogger` events."""

        if event == "cycle_begin":
            self._cycle_started_at = payload.get("ts", self._cycle_started_at)
            if payload.get("cycle_id") is not None:
                try:
                    self._cycle_id = int(payload["cycle_id"])
                except Exception:
                    self._cycle_id = payload.get("cycle_id")

        if self._live is None:
            # Collect events triggered before ``begin`` wires the Live instance.
            self._pending_events.append((event, dict(payload)))
            return

        self._apply_event(event, payload)
        self._refresh()

    def tick(self) -> None:
        """Request a refresh (useful for long-running steps)."""

        self._refresh()

    def end(self, summary: Optional[Dict[str, Any]] = None) -> None:
        """Stop the live table and optionally emit a summary chip."""

        self._refresh(force=True)
        self._stop_live()
        self._pending_events.clear()

        if not summary:
            return

        status = (summary.get("status") or "success").lower()
        text = str(summary.get("text") or "")

        style = _SUMMARY_STYLES.get(status, "bold cyan")
        label = status.upper()
        message = Text.assemble(
            Text(" "),
            Text(label, style=style),
            Text(" • "),
            Text(text, style="default"),
        )
        self.console.print(message)

    def visible_print(self, message: str) -> None:
        """Print a line without disrupting the live layout."""

        self.console.print(message)

    # --------------------------------------------------------------- internals
    def _start_live(self) -> None:
        if self._live is not None:
            self._stop_live()

        self._live = Live(
            self._render_table(),
            console=self.console,
            refresh_per_second=self.refresh_hz,
            transient=False,
            auto_refresh=False,
        )
        self._live.__enter__()

        if self._pending_events:
            for event, payload in list(self._pending_events):
                self._apply_event(event, payload)
            self._pending_events.clear()

    def _stop_live(self) -> None:
        if self._live is None:
            return

        try:
            self._live.update(self._render_table(), refresh=True)
        except Exception:
            pass
        finally:
            self._live.__exit__(None, None, None)
            self._live = None

    def _apply_event(self, event: str, payload: Dict[str, Any]) -> None:
        if event == "cycle_begin":
            return

        if event == "cycle_end":
            self._cycle_ended_at = payload.get("ts", time.time())
            return

        if event not in {"step_start", "step_end"}:
            return

        idx = payload.get("id")
        try:
            idx = int(idx) if idx is not None else None
        except Exception:
            idx = None

        if idx is None:
            return

        activity = self._activities.get(idx)

        if event == "step_start":
            if activity is None:
                activity = dict(payload)
                activity.setdefault("status", "running")
                self._activities[idx] = activity
                self._order.append(idx)
            else:
                activity.update(payload)
            return

        if activity is None:
            return

        activity.update(payload)

    def _refresh(self, *, force: bool = False) -> None:
        if self._live is None:
            return

        now = time.time()
        min_interval = 1.0 / self.refresh_hz if self.refresh_hz > 0 else 0.1
        if not force and (now - self._last_render) < min_interval:
            return

        self._last_render = now
        self._live.update(self._render_table(), refresh=True)

    def _render_table(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column("", width=2)
        table.add_column("Action", justify="left")
        table.add_column("Status", justify="center")
        table.add_column("Time(s)", justify="right")

        now = time.time()
        for idx in self._ordered_indices():
            activity = self._activities.get(idx) or {}
            icon = str(activity.get("icon") or "")
            name = str(activity.get("name") or "")
            status = str(activity.get("status") or "pending").lower()
            started_at = self._safe_float(activity.get("started_at"))
            ended_at = self._safe_float(activity.get("ended_at"))
            duration = self._safe_float(activity.get("duration_s"))

            if status == "running" or duration is None:
                if started_at is not None:
                    duration = max(0.0, (ended_at or now) - started_at)
                else:
                    duration = None

            status_label = _STATUS_LABELS.get(status, status or "?")
            status_style = _STATUS_STYLES.get(status, "white")

            icon_text = Text(icon or "", style="bold")
            action_text = Text(name, style="cyan")
            status_text = Text(status_label, style=status_style)
            time_text = Text("–" if duration is None else f"{duration:.2f}", style="magenta")

            table.add_row(icon_text, action_text, status_text, time_text)

        title = f"Activity — Cycle #{self._cycle_id}" if self._cycle_id is not None else "Activity"
        return Panel(table, border_style="cyan", title=title, padding=(0, 1))

    def _ordered_indices(self) -> Iterable[int]:
        for idx in self._order:
            if idx in self._activities:
                yield idx

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except Exception:
            return None

