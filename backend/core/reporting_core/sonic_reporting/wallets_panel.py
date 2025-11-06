# -*- coding: utf-8 -*-
from __future__ import annotations
"""
wallets_panel — Wallets summary table

Contract (sequencer):
  render(dl, cycle_snapshot_unused, default_json_path=None)

Behavior:
- Source of truth: dl.read_wallets()
- Robust field extraction for dicts and Pydantic/object rows
- Columns: Name | Chain | Address | Balance | USD | Checked
- Prints provenance line like: "[WALLETS] source: dl.read_wallets (N rows)"
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# ───────────────────────── small utils ─────────────────────────

def _to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None

def _fmt_usd(x: Any) -> str:
    f = _to_float(x)
    if f is None:
        return "—"
    sgn = "-" if f < 0 else ""
    f = abs(f)
    if f >= 1_000_000:
        return f"{sgn}${f/1_000_000:.1f}m"
    if f >= 1_000:
        return f"{sgn}${f/1_000:.1f}k"
    return f"{sgn}${f:.0f}" if f >= 100 else f"{sgn}${f:.2f}"

def _fmt_native(x: Any) -> str:
    f = _to_float(x)
    if f is None:
        return "—"
    if abs(f) >= 1_000_000:
        return f"{f/1_000_000:.1f}m"
    if abs(f) >= 1_000:
        return f"{f/1_000:.1f}k"
    return f"{f:.2f}"

def _safe_getattr(obj: Any, name: str, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default

def _field(row: Any, *candidates: str) -> Any:
    """Return first non-empty value across candidate keys; works for dicts and objects."""
    # dict fast path
    if isinstance(row, dict):
        for k in candidates:
            if k in row:
                v = row[k]
                if v not in (None, ""):
                    return v
        # fall through to attr path just in case
    # Pydantic/object dump
    mapper = _safe_getattr(row, "dict", None) or _safe_getattr(row, "model_dump", None)
    data = None
    if callable(mapper):
        try:
            data = mapper()
        except Exception:
            data = None
    if isinstance(data, dict):
        for k in candidates:
            if k in data:
                v = data[k]
                if v not in (None, ""):
                    return v
    # attribute access
    for k in candidates:
        v = _safe_getattr(row, k, None)
        if v not in (None, ""):
            return v
    # item access as final try
    try:
        for k in candidates:
            v = row[k]  # type: ignore[index]
            if v not in (None, ""):
                return v
    except Exception:
        pass
    return None

def _fmt_checked(row: Any) -> str:
    # prefer explicit age seconds
    age = _field(row, "age_s", "age")
    if isinstance(age, (int, float)):
        s = float(age)
        return f"{int(s)}s" if s < 60 else f"{int(s//60)}m"
    # absolute timestamp string
    ts = _field(row, "checked", "updated_at", "ts", "timestamp")
    if isinstance(ts, (int, float)):
        # epoch seconds → hh:mm
        try:
            return datetime.fromtimestamp(float(ts)).strftime("%-I:%M%p").lower()
        except Exception:
            return "(—)"
    if isinstance(ts, str) and ts:
        # show as hh:mm if parseable, else just "(0s)"
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.strftime("%-I:%M%p").lower()
        except Exception:
            return "(0s)"
    return "(0s)"

# ───────────────────────── DL access ─────────────────────────

def _read_wallets(dl: Any) -> Tuple[List[Any], str]:
    """Return (rows, source_label)."""
    try:
        rows = dl.read_wallets()
        try:
            n = len(rows)
        except Exception:
            rows = list(rows)
            n = len(rows)
        print(f"[WALLETS] source: dl.read_wallets ({n} rows)")
        return rows, "dl.read_wallets"
    except Exception as e:
        print(f"[WALLETS] error: {type(e).__name__}: {e}")
        return [], "error"

# ───────────────────────── table builders ─────────────────────────

def _normalize_row(row: Any) -> Tuple[str, str, str, str, str]:
    """
    Map various row schemas to: (name, chain, address, balance_native, usd)
    """
    name = _field(row, "name", "label", "title") or "—"
    chain = _field(row, "chain", "network", "blockchain") or "—"
    addr = _field(row, "address", "pubkey", "public_key") or "—"

    native = _field(row, "balance", "amount", "native", "balance_native")
    usd = _field(row, "usd", "usd_total", "balance_usd", "total_usd", "fiat_usd", "value_usd")

    return (
        str(name),
        str(chain),
        str(addr),
        _fmt_native(native),
        _fmt_usd(usd),
    )

def _total_usd(rows: List[Any]) -> float:
    total = 0.0
    for r in rows:
        v = _field(r, "usd", "usd_total", "balance_usd", "total_usd", "fiat_usd", "value_usd")
        f = _to_float(v)
        if f is not None:
            total += f
    return total

# ───────────────────────── rendering ─────────────────────────

def _render_plain(rows: List[Any]) -> None:
    width = 80
    print("💼 Wallets")
    print("─" * width)
    hdr = f"{'Name':<16} {'Chain':<6} {'Address':<22} {'Balance':>10} {'USD':>8} {'Checked':>9}"
    print(hdr)
    print("─" * len(hdr))
    if not rows:
        total = _fmt_usd(0)
        print(f"{'Total (USD):':>58} {total:>8}")
        return
    for r in rows:
        name, chain, addr, bal, usd = _normalize_row(r)
        chk = _fmt_checked(r)
        print(f"{name:<16} {chain:<6} {addr:<22} {bal:>10} {usd:>8} {chk:>9}")
    print()
    print(f"{'Total (USD):':>58} {_fmt_usd(_total_usd(rows)):>8}")

def _render_rich(rows: List[Any]) -> None:
    try:
        from rich.console import Console
        from rich.text import Text
        from rich.table import Table
        from rich.box import SIMPLE_HEAD
        from rich.measure import Measurement
    except Exception:
        _render_plain(rows)
        return

    console = Console()

    table = Table(
        show_header=True,
        header_style="bold",
        box=SIMPLE_HEAD,
        show_edge=False,
        show_lines=False,
        expand=False,
        pad_edge=False,
    )
    table.add_column("Name")
    table.add_column("Chain")
    table.add_column("Address")
    table.add_column("Balance", justify="right")
    table.add_column("USD", justify="right")
    table.add_column("Checked", justify="right")

    if not rows:
        # Render an empty body but still show a total line below
        pass
    else:
        for r in rows:
            name, chain, addr, bal, usd = _normalize_row(r)
            chk = _fmt_checked(r)
            table.add_row(name, chain, addr, bal, usd, chk)

    # Measure width to size the title rule without echoing
    meas = Measurement.get(console, console.options, table)
    width = max(60, meas.maximum)

    console.print(Text("💼 Wallets".center(width), style="bold bright_cyan"))
    console.print(Text("─" * width, style="bright_cyan"))
    console.print(table)

    # Total line
    console.print(
        Text(
            f"{'Total (USD):':>58} {_fmt_usd(_total_usd(rows)):>8}",
            style="bold",
        )
    )

# ───────────────────────── panel entry ─────────────────────────

def render(dl, _cycle_snapshot_unused, default_json_path=None):
    rows, _ = _read_wallets(dl)
    _render_rich(rows)
