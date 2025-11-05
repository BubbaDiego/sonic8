from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.measure import Measurement


STATUS_STYLE = {
    "success": ("✅", "green"),
    "warn": ("⚠️", "yellow"),
    "fail": ("❌", "red"),
}


def _print_title(console: Console, title: str) -> None:
    console.print(Text.assemble(Text("💼 "), Text(title, style="bold cyan")))


def _status_chip(status: str, err: Optional[str]) -> Text:
    s = (status or "success").lower()
    icon, style = STATUS_STYLE.get(s, ("•", "white"))
    if err:
        return Text.assemble(Text(f"{icon} "), Text(s.capitalize(), style=style), Text(f" — {err}", style="dim"))
    return Text.assemble(Text(f"{icon} "), Text(s.capitalize(), style=style))


def _read_activities_from_dl(dl: Any) -> List[Dict[str, Any]]:
    """Read the latest cycle activities from the DataLocker."""
    if dl is None:
        return []
    if hasattr(dl, "last_cycle") and getattr(dl, "last_cycle") is not None:
        lc = getattr(dl, "last_cycle")
        acts = lc.get("activities") if isinstance(lc, dict) else None
        if isinstance(acts, list):
            return acts
    if hasattr(dl, "cycle_activities"):
        acts = getattr(dl, "cycle_activities")
        if isinstance(acts, list):
            return acts
    return []


def render(dl: Any, csum: Any, default_json_path: Optional[str] = None) -> None:
    """Sequencer contract: render(dl, csum, default_json_path=None)."""
    console = Console()

    activities = _read_activities_from_dl(dl)

    table = Table(show_header=True, header_style="bold", show_lines=False, box=None, pad_edge=False)
    table.add_column("Icon", justify="left", no_wrap=True)
    table.add_column("Action", justify="left", no_wrap=True)
    table.add_column("Time (s)", justify="right", no_wrap=True)
    table.add_column("Status", justify="left", no_wrap=False)

    if not activities:
        table.add_row("-", Text("No recorded steps", style="dim"), "-", Text("—", style="dim"))
    else:
        for a in activities:
            name = str(a.get("name", "-"))
            icon = str(a.get("icon", "•"))
            dur = a.get("duration_s")
            status = str(a.get("status", "success")).lower()
            err = a.get("error")
            action_cell = Text(name, style="blue")
            if isinstance(dur, (int, float)):
                dur_cell = f"{float(dur):.2f}"
            else:
                dur_cell = "-"
            table.add_row(icon, action_cell, dur_cell, _status_chip(status, err))

    _print_title(console, "Cycle Activities")
    meas = Measurement.get(console, console.options, table)
    console.print(Text("─" * max(0, int(meas.maximum)), style="cyan"))
    console.print(f"[CYCLE] steps: {len(activities)}")
    console.print(table)


panel = render
