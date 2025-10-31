# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import List, Optional

from .styles import INDENT, TITLE_STYLE, H, V, TL, TR, BL, BR, TJ, BJ

# Optional Rich console (when present, we render with ZERO borders/lines)
try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    from rich.padding import Padding

    _HAS_RICH = True
except Exception:
    Console = Table = Text = Padding = None  # type: ignore
    _HAS_RICH = False

HAS_RICH = _HAS_RICH
_console = Console() if HAS_RICH else None

TABLE_INDENT = INDENT + "  "
HEADER_STYLE = "bold bright_cyan"


def write_line(text: str) -> None:
    """Print one line with the standard left indent."""
    print(f"{INDENT}{text}", flush=True)


def _rich_with_indent(renderable):
    if not HAS_RICH or _console is None:
        return renderable
    pad_left = len(TABLE_INDENT)
    return Padding(renderable, (0, 0, 0, pad_left)) if Padding else renderable


def write_table(
    title: Optional[str],
    headers: Optional[List[str]],
    rows: List[List[str]],
    align: Optional[List[str]] = None,  # "left" | "center" | "right" per column
) -> None:
    """
    Render a simple table. Sequencer prints section titles; this prints only rows.
    Rich mode: no borders/rules; just a colored header row and data rows.
    ASCII fallback: minimal box top/bottom only (no header spacer).
    """
    # Column count + alignment vector
    ncols = max(len(headers or []), max((len(r) for r in rows), default=0))
    al = list(align or [])
    if len(al) < ncols:
        al += ["left"] * (ncols - len(al))
    al = [a if a in ("left", "center", "right") else "left" for a in al]

    # ---------------------------- Rich mode ----------------------------
    if HAS_RICH and _console is not None and Table is not None:
        tbl = Table(
            show_header=False,
            show_edge=False,
            show_lines=False,
            box=None,
            pad_edge=False,
            expand=False,
            padding=(0, 1),  # compact rows, small cell pad
        )
        for i in range(ncols):
            tbl.add_column(justify=al[i], no_wrap=False)

        if title:
            tbl.add_row(Text(title, style=TITLE_STYLE), *[""] * (ncols - 1))

        if headers:
            hdr_cells: List[Text] = []
            for i in range(ncols):
                text = headers[i] if i < len(headers) else ""
                hdr_cells.append(Text(text, style=HEADER_STYLE, justify="center"))
            tbl.add_row(*hdr_cells)

        for r in rows:
            pad_row = r + [""] * (ncols - len(r))
            tbl.add_row(*pad_row[:ncols])

        _console.print(_rich_with_indent(tbl), justify="left")
        return

    # ------------------------- ASCII fallback --------------------------
    def fit(s):
        return "" if s is None else str(s)

    width = [0] * ncols
    if headers:
        for i, h in enumerate(headers):
            width[i] = max(width[i], len(fit(h)))
    for r in rows:
        for i in range(min(len(r), ncols)):
            width[i] = max(width[i], len(fit(r[i])))

    def line(left: str, mid: str, right: str) -> str:
        return TABLE_INDENT + left + mid.join(H * w for w in width) + right

    top = line(TL, TJ, TR)
    bot = line(BL, BJ, BR)

    print(top)
    if title:
        total = sum(width) + (len(width) - 1)
        t = title if len(title) >= total else title + " " * (total - len(title))
        print(TABLE_INDENT + V + t + V)

    if headers:
        cells = []
        for i, h in enumerate(headers):
            txt, w = fit(h), width[i]
            txt = txt.center(w)
            cells.append(txt)
        print(TABLE_INDENT + V + V.join(cells) + V)

    for r in rows:
        cells = []
        for i in range(ncols):
            txt = fit(r[i]) if i < len(r) else ""
            w, a = width[i], al[i]
            if a == "center":
                txt = txt.center(w)
            elif a == "right":
                txt = txt.rjust(w)
            else:
                txt = txt.ljust(w)
            cells.append(txt)
        print(TABLE_INDENT + V + V.join(cells) + V)

    print(bot, flush=True)
