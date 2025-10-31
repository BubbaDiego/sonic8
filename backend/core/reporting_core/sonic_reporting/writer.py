# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Optional

from .styles import INDENT, TITLE_STYLE, H, V, TL, TR, BL, BR, TJ, BJ

# Optional Rich console
try:
    from rich.console import Console
    from rich.table import Table
    from rich.box import SIMPLE_HEAVY as BOX
    from rich.text import Text
    _HAS_RICH = True
except Exception:
    Console = Table = BOX = Text = None  # type: ignore
    _HAS_RICH = False

_console = Console() if _HAS_RICH else None
HAS_RICH = _HAS_RICH


def write_line(text: str) -> None:
    print(f"{INDENT}{text}", flush=True)


def write_table(
    title: Optional[str],
    headers: Optional[List[str]],
    rows: List[List[str]],
    align: Optional[List[str]] = None,  # per-column alignment: "left"|"center"|"right"
) -> None:
    # Column count + alignment vector
    ncols = max(len(headers or []), max((len(r) for r in rows), default=0))
    al = list(align or [])
    if len(al) < ncols:
        al += ["left"] * (ncols - len(al))
    al = [a if a in ("left", "center", "right") else "left" for a in al]

    if HAS_RICH:
        tbl = Table(show_header=False, show_edge=False, box=BOX, pad_edge=False)
        for i in range(ncols):
            tbl.add_column(justify=al[i], no_wrap=False)
        if title:
            tbl.add_row(Text(title, style=TITLE_STYLE), *[""] * (ncols - 1))
        if headers:
            hdr = [Text(h, style=TITLE_STYLE) for h in headers] + [""] * (ncols - len(headers))
            tbl.add_row(*hdr[:ncols])
        for r in rows:
            pad = r + [""] * (ncols - len(r))
            tbl.add_row(*pad[:ncols])
        _console.print(tbl, justify="left")
        return

    # ASCII fallback
    def fit(s): return "" if s is None else str(s)

    width = [0] * ncols
    if headers:
        for i, h in enumerate(headers):
            width[i] = max(width[i], len(fit(h)))
    for r in rows:
        for i in range(min(len(r), ncols)):
            width[i] = max(width[i], len(fit(r[i])))

    def line(left: str, mid: str, right: str) -> str:
        return INDENT + left + mid.join(H * w for w in width) + right

    top = line(TL, TJ, TR)
    bot = line(BL, BJ, BR)

    print(top)
    if title:
        total = sum(width) + (len(width) - 1)
        t = title if len(title) >= total else title + " " * (total - len(title))
        print(INDENT + V + t + V)

    if headers:
        cells = []
        for i, h in enumerate(headers):
            txt, w, a = fit(h), width[i], al[i]
            if a == "center":
                txt = txt.center(w)
            elif a == "right":
                txt = txt.rjust(w)
            else:
                txt = txt.ljust(w)
            cells.append(txt)
        print(INDENT + V + V.join(cells) + V)

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
        print(INDENT + V + V.join(cells) + V)

    print(bot, flush=True)
