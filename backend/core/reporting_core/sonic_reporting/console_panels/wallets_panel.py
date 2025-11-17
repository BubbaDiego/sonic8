# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List
from datetime import datetime
from io import StringIO
import os
import unicodedata

from rich.console import Console
from rich.table import Table
from rich import box

# standardized   title via console_panels.theming
from backend.core.reporting_core.sonic_reporting.console_panels.theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_above,
    body_pad_below,
    body_indent_lines,
    color_if_plain,
    paint_line,
)

PANEL_SLUG = "wallets"
PANEL_NAME = "Wallets"

INDENT = ""

# legacy widths (not critical now that Rich handles layout)
W_NAME, W_CHAIN, W_ADDR, W_BAL, W_USD, W_CHK = 10, 7, 20, 7, 7, 7
SEP = "  "

try:
    HR_WIDTH = int(os.getenv("SONIC_CONSOLE_WIDTH", "92"))
except Exception:
    HR_WIDTH = 92

# ===== emoji-safe     padding helpers (still used by some text paths) =====
_VAR = {0xFE0F, 0xFE0E}
_ZW = {0x200D, 0x200C}


def _disp_len(s: str) -> int:
    total = 0
    for ch in s:
        cp = ord(ch)
        if cp in _VAR or cp in _ZW:
            continue
        ew = unicodedata.east_asian_width(ch)
        total += 2 if ew in ("W", "F") else 1
    return total


def _padw(text: Any, w: int, *, right: bool = False) -> str:
    s = "" if text is None else str(text)
    cur = _disp_len(s)
    if cur >= w:
        while s and _disp_len(s) > w:
            s = s[:-1]
        return s
    pad = " " * (w - cur)
    return (pad + s) if right else (s + pad)


def _pad(s: Any, w: int, right: bool = False) -> str:
    return _padw(s, w, right=right)


# ===== small formatters =====
def _abbr_addr(a: Any) -> str:
    s = "" if a is None else str(a)
    return "—" if not s else (s if len(s) <= 12 else f"{s[:6]}…{s[-4:]}")


def _fmt_usd_cell(x: Any) -> str:
    """Compact USD formatter (no padding; Rich handles alignment)."""
    try:
        v = float(x)
    except Exception:
        return "—"
    if abs(v) >= 1e6:
        s = f"${v/1e6:.1f}m".replace(".0m", "m")
    elif abs(v) >= 1e3:
        s = f"${v/1e3:.1f}k".replace(".0k", "k")
    else:
        s = f"${v:,.2f}"
    return s


def _fmt_bal_cell(x: Any) -> str:
    """Balance formatter (no padding; Rich handles alignment)."""
    try:
        v = float(x)
    except Exception:
        return "—"
    if abs(v) >= 1e3:
        s = f"{int(round(v))}"
    elif abs(v) >= 1:
        s = f"{v:.2f}"
    elif abs(v) >= 0.01:
        s = f"{v:.3f}"
    else:
        s = f"{v:.4f}"
    return s


def _fmt_age_cell(val: Any) -> str:
    """Age formatter used in the Checked column."""
    try:
        if isinstance(val, (int, float)):
            delta = float(val)
        else:
            t = str(val)
            if t.endswith("Z"):
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(t)
            delta = (datetime.now(dt.tzinfo or None) - dt).total_seconds()
        if delta < 90:
            s = f"{int(delta)}s"
        elif delta < 5400:
            s = f"{int(delta // 60)}m"
        else:
            s = f"{int(delta // 3600)}h"
        return s
    except Exception:
        return "—"


# ===== data =====
def _get_wallets(dl: Any) -> List[Dict[str, Any]]:
    mgr = getattr(dl, "wallets", None)
    if mgr and hasattr(mgr, "get_wallets"):
        try:
            rows = mgr.get_wallets() or []
            return [
                r
                if isinstance(r, dict)
                else (getattr(r, "dict", lambda: {})() or getattr(r, "__dict__", {}) or {})
                for r in rows
            ]
        except Exception as e:
            print(f"[REPORT] wallets_panel: dl.wallets.get_wallets failed: {e}")
    fn = getattr(dl, "read_wallets", None)
    if callable(fn):
        try:
            return fn() or []
        except Exception as e:
            print(f"[REPORT] wallets_panel: dl.read_wallets failed: {e}")
    return []


# ===== Rich table builder =====
def _build_wallets_table(norm: List[Dict[str, Any]], body_cfg: Dict[str, Any]) -> List[str]:
    """
    Build a Rich table for wallets and export as a list of text lines (with ANSI styles).
    - Thin border around the whole table.
    - No per-row grid.
    - Horizontal rule before the totals row.
    """
    table = Table(
        show_header=True,
        header_style="",             # recolor via paint_line later
        show_lines=False,            # no lines between regular rows
        box=box.SIMPLE_HEAD,         # thin border all the way around
        pad_edge=False,
        expand=False,
    )

    # Column headers with icons, matching other panels
    table.add_column("👤 Name", justify="left", no_wrap=True)
    table.add_column("⛓ Chain", justify="left", no_wrap=True)
    table.add_column("🔑 Address", justify="left")
    table.add_column("🪙 Bal", justify="right", no_wrap=True)
    table.add_column("💵 USD", justify="right", no_wrap=True)
    table.add_column("🕒 Checked", justify="right", no_wrap=True)

    total_bal = 0.0
    total_usd = 0.0

    for n in norm:
        try:
            total_bal += float(n.get("bal") or 0.0)
        except Exception:
            pass
        try:
            total_usd += float(n.get("usd") or 0.0)
        except Exception:
            pass

        star = "★ " if n.get("active") else "  "
        name = f"{star}{n.get('name') or '—'}"
        chain = n.get("chain") or "—"
        addr = _abbr_addr(n.get("addr"))
        bal = _fmt_bal_cell(n.get("bal"))
        usd = _fmt_usd_cell(n.get("usd"))
        age = _fmt_age_cell(n.get("chk"))

        table.add_row(name, chain, addr, bal, usd, age)

    totals_style = body_cfg.get("totals_row_color", "")

    # end_section=True draws a horizontal rule ABOVE this row
    table.add_row(
        "",
        "Totals",
        "—",
        _fmt_bal_cell(total_bal),
        _fmt_usd_cell(total_usd),
        "",
        style=totals_style or None,
        end_section=True,
    )

    buf = StringIO()
    console = Console(record=True, width=HR_WIDTH, file=buf, force_terminal=True)
    console.print(table)
    text = console.export_text(styles=True).rstrip("\n")
    if not text:
        return []

    return text.splitlines()


# ===== render =====
def render(dl, *_args, **_kw) -> None:
    rows = _get_wallets(dl)

    print()
    for ln in emit_title_block(PANEL_SLUG, PANEL_NAME):
        print(ln)

    body_cfg = get_panel_body_config(PANEL_SLUG)

    # top padding under title
    for ln in body_pad_above(PANEL_SLUG):
        print(ln)

    if not rows:
        missing = [
            color_if_plain(
                f"{INDENT}[WALLETS] source: dl.wallets.get_wallets (0 rows)",
                body_cfg["body_text_color"],
            ),
            color_if_plain(f"{INDENT}(no wallets)", body_cfg["body_text_color"]),
        ]
        for ln in body_indent_lines(PANEL_SLUG, missing):
            print(ln)
        for ln in body_pad_below(PANEL_SLUG):
            print(ln)
        print()
        return

    # Normalize rows into a common shape
    norm: List[Dict[str, Any]] = []
    for r in rows:
        d = (
            r
            if isinstance(r, dict)
            else (getattr(r, "dict", lambda: {})() or getattr(r, "__dict__", {}) or {})
        )
        norm.append(
            {
                "name": d.get("name") or d.get("label") or "—",
                "chain": d.get("chain")
                or d.get("network")
                or d.get("type")
                or "—",
                "addr": d.get("public_address")
                or d.get("address")
                or d.get("pubkey")
                or d.get("pub_key")
                or "",
                "bal": d.get("balance")
                or d.get("native")
                or d.get("sol")
                or d.get("amount"),
                "usd": d.get("usd")
                or d.get("balance_usd")
                or d.get("fiat_usd"),
                "chk": d.get("checked_at") or d.get("updated_at") or d.get("ts"),
                "active": bool(d.get("is_active")),
            }
        )

    table_lines = _build_wallets_table(norm, body_cfg)

    if not table_lines:
        for ln in body_indent_lines(
            PANEL_SLUG,
            [color_if_plain("(no wallets)", body_cfg["body_text_color"])],
        ):
            print(ln)
        for ln in body_pad_below(PANEL_SLUG):
            print(ln)
        print()
        return

    header_line = table_lines[0]
    data_lines = table_lines[1:]

    # Header with themed color
    header_colored = paint_line(header_line, body_cfg["column_header_text_color"])
    for ln in body_indent_lines(PANEL_SLUG, [header_colored]):
        print(ln)

    # Body lines; keep existing ANSI styles (totals row) and only tint plain ones
    for raw in data_lines:
        for ln in body_indent_lines(
            PANEL_SLUG, [color_if_plain(raw, body_cfg["body_text_color"])]
        ):
            print(ln)

    for ln in body_pad_below(PANEL_SLUG):
        print(ln)
    print()
