from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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

    def stop(self, at: Optional[float] = None) -> None:
        self._stopped = float(at) if at is not None else time.perf_counter()

    def __rich_console__(self, *_: Any) -> RenderResult:
        end = self._stopped if self._stopped is not None else time.perf_counter()
        secs = max(0.0, end - self._start)
        yield Text(f"{secs:0.2f}")


@dataclass
class _Row:
    id: int
    icon: str
    label: str
    timer: _Elapsed
    status: str = "running"
    status_text: Optional[Text] = None
    spinner: Optional[Spinner] = None


_STATUS_STYLE: Dict[str, str] = {
    "": "dim",
    "running": "cyan",
    "success": "green",
    "warn": "yellow3",
    "fail": "red",
}


class CycleActivityStream:
    """Render ActivityLogger events as a borderless Rich table."""

    def __init__(self, console: Optional[Console] = None, *, refresh_hz: float = 10.0) -> None:
        self.console: Console = console or Console()
        self._refresh_hz = float(max(1.0, refresh_hz))
        self._live: Optional[Live] = None
        self._rows: List[_Row] = []
        self._cycle_id: Optional[int] = None

    # ------------------------------------------------------------------ API --

    def begin(self, cycle_id: int) -> None:
        """Start rendering a cycle (prints header once, then the live table)."""
        self._cycle_id = int(cycle_id)
        self._rows.clear()

        self._stop_live()

        title = Text.assemble(
            Text("🦔  "),
            Text("Sonic Monitor Activity — ", style="bold cyan"),
            Text(f"Cycle #{self._cycle_id}", style="bold cyan"),
        )
        self.console.print(title)
        self.console.rule(style="cyan")

        self._start_live()

    def end(self, summary: Optional[Dict[str, Any]] = None) -> None:
        """Stop the live table and optionally print a status chip."""
        self._refresh_live()
        self._stop_live()

        if summary:
            status = str(summary.get("status", "success"))
            style = _STATUS_STYLE.get(status, "green")
            glyph = "✅" if status == "success" else "⚠️" if status == "warn" else "❌"
            msg = str(summary.get("text") or summary.get("summary") or "").strip()
            parts = [
                Text(f"{glyph} ", style=style),
                Text("Sync complete", style=f"bold {style}"),
            ]
            if msg:
                parts.append(Text(f"  {msg}", style="italic"))
            self.console.print(Text.assemble(*parts))

    def tick(self) -> None:
        """Manual refresh helper for long-running steps."""
        if self._live is not None:
            self._live.refresh()

    def visible_print(self, message: str) -> None:
        """Print a line without breaking the live layout."""
        self.console.print(message)
        self._refresh_live()

    def on_event(self, event: str, payload: Dict[str, Any]) -> None:
        if event == "step_start":
            self._on_step_start(payload)
        elif event == "step_end":
            self._on_step_end(payload)

    # -------------------------------------------------------------- internals

    def _start_live(self) -> None:
        table = self._build_table()
        self._live = Live(
            table,
            console=self.console,
            refresh_per_second=self._refresh_hz,
            transient=False,
            auto_refresh=True,
        )
        self._live.__enter__()
        self._refresh_live()

    def _stop_live(self) -> None:
        if self._live is not None:
            try:
                self._live.update(self._build_table())
            finally:
                self._live.__exit__(None, None, None)
                self._live = None

    def _refresh_live(self) -> None:
        if self._live is not None:
            self._live.update(self._build_table())

    def _on_step_start(self, payload: Dict[str, Any]) -> None:
        rid = int(payload.get("id", len(self._rows)))
        icon = str(payload.get("icon") or "•")
        label = str(payload.get("name") or "")
        started = self._safe_float(payload.get("started_at"), time.perf_counter())
        row = _Row(
            id=rid,
            icon=icon,
            label=label,
            timer=_Elapsed(started),
            status="running",
            status_text=None,
            spinner=Spinner("dots", text="", style="cyan"),
        )
        self._rows.append(row)
        self._refresh_live()

    def _on_step_end(self, payload: Dict[str, Any]) -> None:
        rid = int(payload.get("id", -1))
        status = str(payload.get("status", "success"))
        ended_at = self._safe_float(payload.get("ended_at"))
        error_text = payload.get("error")
        for row in self._rows:
            if row.id == rid:
                row.status = status
                row.timer.stop(ended_at)
                row.spinner = None
                row.status_text = self._status_chip(status, error_text)
                break
        self._refresh_live()

    def _status_chip(self, status: str, error: Optional[str]) -> Text:
        style = _STATUS_STYLE.get(status, "green")
        if status == "success":
            glyph, label = "✅", "Success"
        elif status == "warn":
            glyph, label = "⚠️", "Warn"
        elif status == "fail":
            glyph, label = "❌", "Fail"
        else:
            glyph, label = "⏳", "Running"
        chip = Text.assemble(Text(f"{glyph} ", style=style), Text(label, style=style))
        if error:
            chip.append(f"  {error}", style="italic")
        return chip

    def _build_table(self) -> Table:
        table = Table(
            show_header=True,
            header_style="bold",
            box=None,
            pad_edge=False,
            expand=True,
        )
        table.add_column("Activity", justify="left", no_wrap=False)
        table.add_column("Status", justify="left", no_wrap=False)
        table.add_column("Time (s)", justify="right", no_wrap=True)
        table.add_column("⟳", justify="right", no_wrap=True, width=2)

        for row in self._rows:
            activity = Text.assemble(Text(f"{row.icon} "), Text(row.label, style="deepsky_blue2"))
            status = row.status_text or self._status_chip(row.status, None)
            spinner = row.spinner if row.spinner is not None else Text("")
            table.add_row(activity, status, row.timer, spinner)
        return table

    @staticmethod
    def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        if value is None:
            return default
        try:
            return float(value)
        except Exception:
            return default
