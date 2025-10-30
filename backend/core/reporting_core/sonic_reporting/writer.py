# -*- coding: utf-8 -*-
from __future__ import annotations
import importlib
from typing import List, Optional
from .styles import INDENT, TITLE_STYLE, H, V, TL, TR, BL, BR, TJ, BJ, VJ

# Rich detection (optional)
try:
    rich_console = importlib.import_module("rich.console"); Console = getattr(rich_console, "Console")
    rich_table   = importlib.import_module("rich.table");   Table   = getattr(rich_table, "Table")
    rich_box     = importlib.import_module("rich.box");     BOX     = getattr(rich_box, "SIMPLE_HEAVY")
    rich_text    = importlib.import_module("rich.text");    Text    = getattr(rich_text, "Text")
    _HAS_RICH = True
except Exception:
    _HAS_RICH = False
    Console = Table = BOX = Text = None  # type: ignore

_console = Console() if _HAS_RICH else None

# Expose Rich availability for callers that need to adjust ANSI formatting.
HAS_RICH = _HAS_RICH

def write_line(text: str) -> None:
    print(f"{INDENT}{text}", flush=True)

def write_table(title: Optional[str], headers: Optional[List[str]], rows: List[List[str]]) -> None:
    if _HAS_RICH:
        # No outer border and no section separators -> eliminates “blank line” feel
        tbl = Table(show_header=False, show_edge=False, box=BOX, pad_edge=False)
        ncols = max(len(headers or []), max((len(r) for r in rows), default=0))
        for _ in range(ncols):
            tbl.add_column(justify="left", no_wrap=False)
        if title:
            # No end_section here; we want title immediately followed by headers/rows
            tbl.add_row(Text(title, style=TITLE_STYLE), *[""]*(ncols-1))
        if headers:
            # No end_section; keep headers tight to the first data row
            tbl.add_row(*[Text(h, style=TITLE_STYLE) for h in headers])
        for r in rows:
            pad = r + [""]*(ncols-len(r))
            tbl.add_row(*pad)
        _console.print(tbl, justify="left")
        return

    # ASCII fallback (draw top/bottom borders but no header separator lines)
    cols = headers or (rows[0] if rows else [])
    ncols = max(len(cols), max((len(r) for r in rows), default=0))
    width = [0]*ncols
    def fit(s): return str(s) if s is not None else ""
    # compute widths
    def upd(arr):
        for i, s in enumerate(arr):
            width[i] = max(width[i], len(fit(s)))
    if headers: upd(headers)
    for r in rows: upd(r)
    width = [max(w, 4) for w in width]

    def line_left_mid_right(left, mid, right):
        segs = [H*w for w in width]
        return INDENT + left + (mid.join(segs)) + right

    top = line_left_mid_right(TL, TJ, TR)
    bot = line_left_mid_right(BL, BJ, BR)
    # sep = line_left_mid_right("├", VJ, "┤")  # not used: we removed header separators

    print(top)
    if title:
        t = (title + " " * (sum(width) + (ncols-1) - len(title))) if (sum(width)+(ncols-1)) > len(title) else title
        print(INDENT + V + t + V)
        # no separator here
    if headers:
        hdr = INDENT + V + V.join(fit(h).ljust(width[i]) for i, h in enumerate(headers)) + V
        print(hdr)  # no separator after headers
    for r in rows:
        row = INDENT + V + V.join(fit(r[i]).ljust(width[i]) if i < len(r) else " "*width[i] for i in range(ncols)) + V
        print(row)
    print(bot, flush=True)
