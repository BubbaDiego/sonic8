from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

# Optional Rich; degrade gracefully if missing.
try:  # pragma: no cover - optional dependency
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except Exception:  # pragma: no cover - graceful fallback when Rich missing
    Console = None  # type: ignore[assignment]
    Table = None  # type: ignore[assignment]
    Panel = None  # type: ignore[assignment]
    box = None  # type: ignore[assignment]


def _console() -> Optional[Console]:
    return Console() if Console else None


def panel(title: str, body: str) -> None:
    cn = _console()
    if not cn or Panel is None:
        print(f"[{title}]\n{body}\n")
        return
    cn.print(Panel(body, title=title, border_style="cyan", expand=False))


def kv_table(title: str, data: Dict[str, Any]) -> None:
    cn = _console()
    if not cn or Table is None:
        print(f"\n== {title} ==")
        for k, v in data.items():
            print(f"- {k}: {v}")
        return
    t = Table(title=title, box=box.SIMPLE, expand=False)  # type: ignore[union-attr]
    t.add_column("Key", style="bold cyan")
    t.add_column("Value")
    for k, v in data.items():
        t.add_row(str(k), str(v))
    cn.print(t)


def rows_table(title: str, columns: Iterable[str], rows: Iterable[Iterable[Any]]) -> None:
    cn = _console()
    if not cn or Table is None:
        print(f"\n== {title} ==")
        print(", ".join(columns))
        for r in rows:
            print(", ".join(str(x) for x in r))
        return
    t = Table(title=title, box=box.MINIMAL_DOUBLE_HEAD, expand=False)  # type: ignore[union-attr]
    for col in columns:
        t.add_column(str(col))
    for r in rows:
        t.add_row(*[str(x) for x in r])
    cn.print(t)
