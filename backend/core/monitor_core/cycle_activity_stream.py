"""Live cycle activity table rendered with Rich."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from rich.console import Console, RenderResult
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text


class _Elapsed:
    """Renderable timer cell that continually updates until stopped."""

    def __init__(self, start: float) -> None:
        self._start = float(start)
        self._stopped: Optional[float] = None

    def reset(self, start: float) -> None:
        self._start = float(start)
        self._stopped = None

    def stop(self, t: Optional[float] = None) -> None:
        self._stopped = float(t) if t is not None else time.perf_counter()

    def __rich_console__(self, *_: Any) -> RenderResult:
        end = self._stopped if self._stopped is not None else time.perf_counter()
        yield Text(f"{max(0.0, end - self._start):0.2f}")


_STATUS_STYLE: Dict[str, str] = {
    "": "dim",
    "pending": "dim",
    "running": "cyan",
    "success": "green",
    "warn": "yellow3",
    "warning": "yellow3",
    "fail": "red",
    "error": "red",
}


@dataclass
class _Row:
    id: Any
    icon: str
    label: str
    timer: _Elapsed
    status: str = "running"
    status_text: Optional[Text] = None
    spinner: Optional[Spinner] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None


class CycleActivityStream:
    """Render :class:`ActivityLogger` events as a live Rich table."""

    def __init__(self, console: Optional[Console] = None, *, refresh_per_sec: float = 10.0) -> None:
        self.console = console or Console()
        self._refresh_hz = max(1.0, float(refresh_per_sec))

        self._live: Optional[Live] = None
        self._rows: Dict[Any, _Row] = {}
        self._order: List[Any] = []
        self._cycle_id: Optional[Any] = None
        self._cycle_started_at: Optional[float] = None
        self._pending_events: List[Tuple[str, Dict[str, Any]]] = []
        self._last_render: float = 0.0

    # ------------------------------------------------------------------ API
    def begin(self, cycle_id: int) -> None:
        """Start rendering a new cycle."""

        self._cycle_id = cycle_id
        self._cycle_started_at = time.perf_counter()
        self._rows.clear()
        self._order.clear()

        self._print_header()
        self._start_live()

        if self._pending_events:
            for event, payload in list(self._pending_events):
                self._apply_event(event, payload)
            self._pending_events.clear()

        self._update_live(force=True)

    def on_event(self, event: str, payload: Dict[str, Any]) -> None:
        """Mirror :class:`ActivityLogger` events."""

        if event == "cycle_begin":
            self._handle_cycle_begin(payload)
            if self._live is None:
                self._pending_events.append((event, dict(payload)))
            return

        if self._live is None:
            self._pending_events.append((event, dict(payload)))
            return

        self._apply_event(event, payload)
        self._update_live()

    def tick(self) -> None:
        """Request a refresh (useful for long-running steps)."""

        self._update_live()

    def end(self, summary: Optional[Dict[str, Any]] = None) -> None:
        """Stop the live table and optionally emit a summary chip."""

        self._update_live(force=True)
        self._stop_live()
        self._pending_events.clear()

        if not summary:
            return

        status = self._normalize_status(summary.get("status", "success"))
        style = _style_for(status)
        icon = _summary_icon(status)
        message = str(summary.get("text") or summary.get("summary") or "").strip()

        parts = [
            Text(f"{icon} ", style=style),
            Text("Sync complete", style=f"bold {style}"),
        ]
        if message:
            parts.append(Text(f"  {message}", style="italic"))

        self.console.print(Text.assemble(*parts))

    def visible_print(self, message: str) -> None:
        """Print a line without disrupting the live layout."""

        self.console.print(message)
        if self._live is not None:
            self._update_live(force=True)

    # --------------------------------------------------------------- internals
    def _print_header(self) -> None:
        title = Text.assemble(
            Text("🦔  ", style="bold"),
            Text(
                f"Sonic Monitor Activity — Cycle #{self._cycle_id}",
                style="bold cyan",
            ),
        )
        self.console.print(title)
        self.console.rule(style="cyan")

    def _handle_cycle_begin(self, payload: Dict[str, Any]) -> None:
        cycle_id = payload.get("cycle_id")
        norm_id = self._normalize_id(cycle_id)
        if norm_id is not None:
            self._cycle_id = norm_id
        started = self._safe_float(payload.get("ts"))
        if started is not None:
            self._cycle_started_at = started

    def _start_live(self) -> None:
        if self._live is not None:
            self._stop_live()

        self._live = Live(
            self._build_table(),
            console=self.console,
            refresh_per_second=self._refresh_hz,
            transient=False,
            auto_refresh=False,
        )
        self._live.__enter__()
        self._last_render = 0.0

    def _stop_live(self) -> None:
        if self._live is None:
            return

        try:
            self._live.update(self._build_table(), refresh=True)
        finally:
            self._live.__exit__(None, None, None)
            self._live = None
            self._last_render = 0.0

    def _apply_event(self, event: str, payload: Dict[str, Any]) -> None:
        if event == "step_start":
            self._on_step_start(payload)
        elif event == "step_end":
            self._on_step_end(payload)

    def _on_step_start(self, payload: Dict[str, Any]) -> None:
        rid = self._normalize_id(payload.get("id"))
        if rid is None:
            rid = self._allocate_id()

        label = str(payload.get("name") or "")
        icon = str(payload.get("icon") or "•")
        started_at = self._safe_float(payload.get("started_at")) or time.perf_counter()

        row = self._rows.get(rid)
        if row is None:
            row = _Row(
                id=rid,
                icon=icon,
                label=label,
                timer=_Elapsed(started_at),
                status="running",
                spinner=Spinner("dots", text="", style="cyan"),
            )
            self._rows[rid] = row
            self._order.append(rid)
        else:
            row.icon = icon or row.icon
            row.label = label or row.label
            row.status = "running"
            row.status_text = None
            row.error = None
            row.finished_at = None
            if row.timer is None:
                row.timer = _Elapsed(started_at)
            else:
                row.timer.reset(started_at)
            row.spinner = Spinner("dots", text="", style="cyan")

    def _on_step_end(self, payload: Dict[str, Any]) -> None:
        rid = self._normalize_id(payload.get("id"))
        if rid is None:
            return

        row = self._rows.get(rid)
        if row is None:
            started_at = self._safe_float(payload.get("started_at")) or time.perf_counter()
            row = _Row(
                id=rid,
                icon=str(payload.get("icon") or "•"),
                label=str(payload.get("name") or ""),
                timer=_Elapsed(started_at),
            )
            self._rows[rid] = row
            self._order.append(rid)

        status = self._normalize_status(
            payload.get("e_status") or payload.get("status") or "success"
        )
        row.status = status

        ended_at = self._safe_float(payload.get("ended_at")) or time.perf_counter()
        row.timer.stop(ended_at)
        row.finished_at = ended_at
        row.spinner = None

        error = payload.get("error")
        row.error = str(error) if error else None

        style = _style_for(status)
        label = _status_label(status)
        icon = _status_icon(status)

        segments = [Text(f"{icon} ", style=style), Text(label, style=style)]
        if row.error:
            segments.append(Text(f"  {row.error}", style="italic"))

        row.status_text = Text.assemble(*segments)

    def _allocate_id(self) -> int:
        candidate = len(self._order)
        while candidate in self._rows:
            candidate += 1
        return candidate

    def _update_live(self, *, force: bool = False) -> None:
        if self._live is None:
            return

        now = time.perf_counter()
        min_interval = 1.0 / self._refresh_hz if self._refresh_hz > 0 else 0.1
        if not force and (now - self._last_render) < min_interval:
            return

        self._last_render = now
        self._live.update(self._build_table(), refresh=True)

    def _build_table(self) -> Table:
        table = Table(
            show_header=True,
            header_style="bold",
            show_lines=False,
            box=None,
            pad_edge=False,
        )
        table.add_column("Activity", justify="left", no_wrap=False)
        table.add_column("Status", justify="left", no_wrap=True)
        table.add_column("Time (s)", justify="right", no_wrap=True)
        table.add_column(" ", justify="right", width=2)

        for row in self._iter_rows():
            activity = Text.assemble(Text(f"{row.icon} "), Text(row.label, style="deepsky_blue2"))
            status = row.status_text or Text("⏳ Running", style=_style_for("running"))
            timer = row.timer
            spinner = row.spinner or Text("")
            table.add_row(activity, status, timer, spinner)

        return table

    def _iter_rows(self) -> Iterable[_Row]:
        for rid in self._order:
            row = self._rows.get(rid)
            if row is not None:
                yield row

    @staticmethod
    def _normalize_id(value: Any) -> Optional[Any]:
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            try:
                return str(value)
            except Exception:
                return None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _normalize_status(value: Any) -> str:
        if not value:
            return ""
        status = str(value).strip().lower()
        if status == "warning":
            return "warn"
        if status == "error":
            return "fail"
        return status


def _status_label(status: str) -> str:
    if status == "success":
        return "Success"
    if status == "warn":
        return "Warn"
    if status == "fail":
        return "Fail"
    if status == "running":
        return "Running"
    if status == "pending":
        return "Pending"
    return status.title() if status else "Done"


def _status_icon(status: str) -> str:
    if status == "success":
        return "✅"
    if status == "warn":
        return "⚠️"
    if status == "fail":
        return "❌"
    if status == "running":
        return "⏳"
    return "•"


def _summary_icon(status: str) -> str:
    if status == "success":
        return "✅"
    if status == "warn":
        return "⚠️"
    if status == "fail":
        return "❌"
    return "✅"


def _style_for(status: str) -> str:
    return _STATUS_STYLE.get(status, "green")

