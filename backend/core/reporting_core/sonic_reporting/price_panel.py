# -*- coding: utf-8 -*-
from __future__ import annotations
"""
price_panel — DL-sourced prices with a Rich bordered table (no csum dependency)

Signature (sequencer contract):
  render(dl, csum, default_json_path=None)
"""

from typing import Any, Dict, Optional, Tuple

# Panel UI options
PRICE_BORDER  = "light"          # "light" | "none"
TITLE_COLOR   = "bright_cyan"    # Rich color name for the title text
BORDER_COLOR  = "bright_cyan"    # Match the small underline color you liked

ASSETS = ("BTC", "ETH", "SOL")
ICON   = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}

from backend.data.data_locker import DataLocker


# ─────────────────────── utils ───────────────────────

def _ensure_dl(dl: Optional[DataLocker]) -> DataLocker:
    if dl is not None:
        return dl
    try:
        return DataLocker.get_instance(r"C:\sonic7\backend\mother.db")
    except Exception:
        return DataLocker.get_instance()

def _fmt_price(x: Optional[float]) -> str:
    if x is None:
        return "—"
    v = float(x)
    a = abs(v)
    if a >= 1_000_000:  return f"{v/1_000_000:.1f}m"
    if a >= 1_000:      return f"{v/1_000:.1f}k"
    return f"{v:.2f}"

def _fmt_delta(cur: Optional[float], prev: Optional[float]) -> Tuple[str, str]:
    if cur is None or prev is None:
        return ("—", "—")
    d   = float(cur) - float(prev)
    pct = (d / float(prev) * 100.0) if float(prev) != 0 else 0.0
    s   = "+" if d >= 0 else ""
    return (f"{s}{d:.2f}", f"{s}{pct:.2f}%")

def _fmt_checked(info: Dict[str, Any]) -> str:
    age = info.get("age_s") or info.get("age")
    if isinstance(age, (int, float)):
        s = float(age)
        if s < 60:
            return f"{int(s)}s"
        return f"{int(s//60)}m"
    if info.get("checked") or info.get("ts"):
        return "(0s)"
    return "(—)"

def _read_from_dl(dl: DataLocker, sym: str) -> Tuple[Optional[float], Optional[float], str]:
    try:
        info = getattr(dl, "get_latest_price", lambda *_: {})(sym) or {}
        cur  = info.get("current_price") or info.get("current") or info.get("price")
        prev = info.get("previous") or info.get("prev")
        cur  = float(cur)  if cur  is not None else None
        prev = float(prev) if prev is not None else None
        checked = _fmt_checked(info)
        return cur, prev, checked
    except Exception:
        return None, None, "(—)"


# ─────────────────────── rendering ───────────────────────

def _center_text(title: str, width: int) -> str:
    # Center title within an exact width (no filler chars)
    pad = max(0, (width - len(title)) // 2)
    return " " * pad + title

def _render_bordered(rows: list[list[str]], header: list[str], title: str) -> None:
    try:
        from rich.table import Table
        from rich.console import Console
        from rich.box import SIMPLE_HEAD
        from rich.text import Text
    except Exception:
        _render_unbordered(rows, header, title)
        return

    console = Console()

    # Build the table FIRST so we can compute its exact rendered width.
    table = Table(
        show_header=True,
        header_style="bold",
        box=SIMPLE_HEAD,             # keeps the small underline under header row
        border_style=BORDER_COLOR,   # color for header underline; match our solid line
        show_edge=False,             # no outer box
        show_lines=False,
        expand=False,
        pad_edge=False,
    )
    for col in header:
        table.add_column(col)

    for r in rows:
        table.add_row(*[str(c) for c in r])

    # Measure exact rendered width so our lines match the table width precisely
    rec = Console(record=True, width=console.width)
    rec.print(table)
    rendered = rec.export_text(clear=False)
    table_width = max((len(line.rstrip("\n")) for line in rendered.splitlines()), default=60)

    # Title on its own line (centered), then a SOLID line of same length/color as the header underline.
    title_line = _center_text("💰 Prices", table_width)
    console.print(Text(title_line, style=f"bold {TITLE_COLOR}"))
    console.print(Text("─" * table_width, style=BORDER_COLOR))

    # Now the table (no extra newline in between beyond the prints above)
    console.print(table)

def _render_unbordered(rows: list[list[str]], header: list[str], title: str) -> None:
    # Plain-text fallback: estimate width from header/row lengths
    width = max(
        len("  " + "  ".join(header)),
        max((len("  " + "  ".join(str(c) for c in r)) for r in rows), default=0),
        60,
    )
    # Title line then solid line
    print(_center_text("💰 Prices", width))
    print("─" * width)
    # header
    widths = [max(len(str(header[c])), max(len(str(r[c])) for r in rows) if rows else 0)
              for c in range(len(header))]
    print("  " + "  ".join(str(header[c]).ljust(widths[c]) for c in range(len(header))))
    # rows
    for r in rows:
        print("  " + "  ".join(str(r[c]).ljust(widths[c]) for c in range(len(header))))


# ─────────────────────── panel entry ───────────────────────

def render(dl, csum, default_json_path=None):
    """
    DL-only prices (BTC/ETH/SOL) with a Rich table styled like sync_panel.
    """
    dl = _ensure_dl(dl)

    header = ["Asset", "Current", "Previous", "Δ", "Δ%", "Checked"]
    rows: list[list[str]] = []

    for sym in ASSETS:
        cur, prev, checked = _read_from_dl(dl, sym)
        d, pct = _fmt_delta(cur, prev)
        rows.append([
            f"{ICON.get(sym,'•')} {sym}",
            _fmt_price(cur),
            _fmt_price(prev),
            d,
            pct,
            checked,
        ])

    if PRICE_BORDER == "light":
        _render_bordered(rows, header, "💰 Prices")
    else:
        _render_unbordered(rows, header, "💰 Prices")

    print(f"\n[PRICE] source: dl.get_latest_price")
