# -*- coding: utf-8 -*-
from __future__ import annotations
"""
price_panel — DL-sourced prices with a Rich bordered table (no csum dependency)

Panel-local options:
  PRICE_BORDER = "light" | "none"
  TITLE_COLOR  = <rich color>
  BORDER_COLOR = <rich color>

Signature (matches sequencer):
  render(dl, csum, default_json_path=None)
"""

from typing import Any, Dict, Optional, Tuple

# Panel UI options (tweak here)
PRICE_BORDER  = "light"          # "light" | "none"
TITLE_COLOR   = "bright_cyan"    # Rich color name
BORDER_COLOR  = "bright_black"   # Rich color name

ASSETS = ("BTC", "ETH", "SOL")
ICON   = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}

# DataLocker (panel-local source of truth)
from backend.data.data_locker import DataLocker


# ──────────────────────── small utils ────────────────────────

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
    # Try a few common forms: 'age_s', 'age', 'checked', 'ts'
    age = info.get("age_s") or info.get("age")
    if isinstance(age, (int, float)):
        s = float(age)
        if s < 60:
            return f"{int(s)}s"
        return f"{int(s//60)}m"
    # a timestamp-like field (ignore actual formatting; keep "(0s)"-style)
    if info.get("checked") or info.get("ts"):
        return "(0s)"
    return "(—)"

def _read_from_dl(dl: DataLocker, sym: str) -> Tuple[Optional[float], Optional[float], str]:
    """
    Return (current, previous, checked_label) from DataLocker price cache.
    """
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


# ──────────────────────── rendering ────────────────────────

def _render_bordered(rows: list[list[str]], header: list[str], title: str) -> None:
    try:
        from rich.table import Table
        from rich.console import Console
        from rich.box import SIMPLE
    except Exception:
        _render_unbordered(rows, header, title)  # graceful fallback
        return

    table = Table(
        title=f"[{TITLE_COLOR}]{title}[/{TITLE_COLOR}]",
        show_header=True,
        header_style="bold",
        box=SIMPLE,
        border_style=BORDER_COLOR,
        title_justify="left",
        show_edge=True,
        show_lines=False,
        expand=False,
        pad_edge=False,
    )
    for col in header:
        table.add_column(col)

    for r in rows:
        table.add_row(*[str(c) for c in r])

    Console().print(table)


def _render_unbordered(rows: list[list[str]], header: list[str], title: str) -> None:
    print(f"\n  {title}\n")
    widths = [max(len(str(header[c])), max(len(str(r[c])) for r in rows) if rows else 0)
              for c in range(len(header))]
    print("  " + "  ".join(str(header[c]).ljust(widths[c]) for c in range(len(header))))
    print("")
    for r in rows:
        print("  " + "  ".join(str(r[c]).ljust(widths[c]) for c in range(len(header))))


# ──────────────────────── panel entry ────────────────────────

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

    title = "💰 Prices"
    if PRICE_BORDER == "light":
        _render_bordered(rows, header, title)
    else:
        _render_unbordered(rows, header, title)

    print(f"\n[PRICE] source: dl.get_latest_price")
