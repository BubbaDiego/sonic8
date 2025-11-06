# -*- coding: utf-8 -*-
from __future__ import annotations
"""
monitor_panel — Monitors table (Liquid & Profit)

Contract (sequencer):
  render(dl, cycle_snapshot_unused, default_json_path=None)

Behavior:
- Thresholds: JSON (supports legacy + monitor keys)
  Liquid:
    • liquid_monitor.thresholds           → preferred
    • liquid.thresholds                   → fallback
  Profit:
    • profit_monitor.position_profit_usd / portfolio_profit_usd → preferred
    • profit.position_usd / portfolio_usd                        → fallback
- Values: from dl.read_positions() + dl.get_latest_price(symbol) (for mark)
- Outcome: Liquid -> value ≤ threshold ; Profit -> value ≥ threshold
- Source:  "JSON:…" (threshold provenance, e.g., profit_monitor vs legacy)
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple
from pathlib import Path
import json
import os
import re

from backend.core.reporting_core.sonic_reporting.threshold_resolvers import (
    resolve_liquid_thresholds,
    resolve_profit_thresholds,
)
TITLE = "🧭 Monitors"
TITLE_COLOR = "bright_cyan"
RULE_COLOR  = "bright_cyan"

ICON_LIQUID = "💧"
ICON_PROFIT = "💵"

BREACH    = "BREACH"
NO_BREACH = "no breach"

DEFAULT_CONFIG_PATH = Path("backend/config/sonic_monitor_config.json")
FALLBACK_SYMBOLS = ("BTC", "ETH", "SOL")

# Set True briefly to inspect what the panel sees (positions, thresholds, values)
DEBUG_MONITOR_PANEL = False


# ───────────────────────── core utils ─────────────────────────

def _to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None

def _fmt_num(x: Any) -> str:
    f = _to_float(x)
    if f is None:
        return "—"
    a = abs(f)
    if a >= 1_000_000: return f"{f/1_000_000:.1f}m"
    if a >= 1_000:     return f"{f/1_000:.1f}k"
    if f == int(f):    return f"{int(f)}"
    return f"{f:.2f}"

def _fmt_money(x: Any) -> str:
    f = _to_float(x)
    if f is None:
        return "—"
    sign = "-" if f < 0 else ""
    f = abs(f)
    if f >= 1_000_000: return f"{sign}${f/1_000_000:.1f}m"
    if f >= 1_000:     return f"{sign}${f/1_000:.1f}k"
    return f"{sign}${f:.2f}"

def _load_config(default_json_path: Optional[str | os.PathLike]) -> Dict[str, Any]:
    path = Path(default_json_path) if default_json_path else DEFAULT_CONFIG_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _safe_getattr(obj: Any, name: str, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default

# Robust access for dicts, Pydantic models, and plain objects
def _field(row: Any, *candidates: str) -> Any:
    if isinstance(row, dict):
        for k in candidates:
            if k in row:
                v = row[k]
                if v is not None and v != "":
                    return v
        return None
    dct = None
    to_dict = _safe_getattr(row, "dict", None) or _safe_getattr(row, "model_dump", None)
    if callable(to_dict):
        try: dct = to_dict()
        except Exception: dct = None
    if isinstance(dct, dict):
        for k in candidates:
            if k in dct:
                v = dct[k]
                if v is not None and v != "":
                    return v
    for k in candidates:
        v = _safe_getattr(row, k, None)
        if v is not None and v != "":
            return v
    try:
        for k in candidates:
            v = row[k]  # type: ignore[index]
            if v is not None and v != "":
                return v
    except Exception:
        pass
    return None

# Normalize symbols so JSON keys and position symbols match
# Examples:
#   SOL-PERP  → SOL
#   BTC_PERP  → BTC
#   ETH/USDC  → ETH
#   sol       → SOL
def _norm_sym(s: str | None) -> Optional[str]:
    if not s:
        return None
    t = s.strip().upper()
    if "/" in t:
        t = t.split("/", 1)[0]
    t = re.sub(r"[-_]?PERP$", "", t)
    # keep left side only if exchange suffixes remain (e.g., SOL.P)
    t = re.split(r"[.\-_:]", t)[0]
    return t or None


# ───────────────────────── thresholds (JSON → DL accessor) ─────────────────────────

# ───────────────────────── values (from positions + price) ─────────────────────────

def _read_positions(dl: Any) -> List[Any]:
    try:
        rows = dl.read_positions()
        return list(rows) if not isinstance(rows, list) else rows
    except Exception:
        return []

def _symbol_of(row: Any) -> Optional[str]:
    # PositionDB uses 'asset_type'
    raw = _field(row, "asset_type", "asset", "symbol", "base", "ticker", "asset_symbol")
    return _norm_sym(raw) if isinstance(raw, str) else None

def _latest_mark(dl: Any, sym: str) -> Optional[float]:
    """Use DL’s price path if the row lacks a mark."""
    try:
        info = getattr(dl, "get_latest_price", lambda *_: {})(sym) or {}
        mark = info.get("current_price") or info.get("current") or info.get("price")
        return float(mark) if mark is not None else None
    except Exception:
        return None

def _liq_distance_pct_of(row: Any, sym_norm: str, dl: Any) -> Optional[float]:
    """
    Distance to liquidation (%):
      1) if a percent-like field exists AND looks like a real percent (0..100), use it:
         liquidation_distance, liquidation, liq, liq_dist, liq_pct, dist_to_liq_pct, distance_liq_pct
      2) else compute: |mark - liq_price| / mark * 100,
         using row's mark/price or DL's latest price as fallback.
    """
    v = _field(row, "liquidation_distance", "liquidation", "liq", "liq_dist",
                     "liq_pct", "dist_to_liq_pct", "distance_liq_pct")
    fv = _to_float(v)
    if fv is not None and 0.0 <= fv <= 100.0:
        return fv

    liq_price = _field(row, "liq_price", "liquidation_price", "liquidation", "liq_px", "liqPrice")
    liq_f = _to_float(liq_price)
    if liq_f is None:
        return None

    mark = _field(row, "mark_price", "price", "current_price", "mark", "mark_px", "index_price", "oracle_price", "mid_price")
    mark_f = _to_float(mark) if mark is not None else None
    if mark_f is None:
        mark_f = _latest_mark(dl, sym_norm)

    if mark_f is None or mark_f == 0:
        return None

    return abs((mark_f - liq_f) / mark_f) * 100.0

def _liquid_values_from_positions(rows: List[Any], dl: Any) -> Dict[str, float]:
    """
    For each normalized symbol, take the minimal distance-to-liquidation (worst case).
    """
    best: Dict[str, float] = {}
    for r in rows:
        sym = _symbol_of(r)
        if not sym:
            continue
        d = _liq_distance_pct_of(r, sym, dl)
        if d is None:
            continue
        if sym not in best or d < best[sym]:
            best[sym] = d
    return best

def _profit_values_from_positions(rows: List[Any]) -> Dict[str, float]:
    """
    'single'    : max positive PnL across positions (0 if none positive)
    'portfolio' : net sum PnL across positions
    """
    max_pos = 0.0
    total   = 0.0
    for r in rows:
        v = _field(r, "pnl", "unrealized_pnl", "upnl", "pnl_usd")
        f = _to_float(v)
        if f is None:
            continue
        total += f
        if f > max_pos:
            max_pos = f
    return {"single": max_pos, "portfolio": total}


# ───────────────────────── row assembly ─────────────────────────

def _build_rows_from_json_and_positions(
    dl: Any,
    cfg: Dict[str, Any],
) -> List[Tuple[str, str, str, str, str]]:
    rows_out: List[Tuple[str, str, str, str, str]] = []

    positions = _read_positions(dl)
    if DEBUG_MONITOR_PANEL:
        print(f"[MON] positions read: {len(positions)}")
        for i, r in enumerate(positions[:3]):
            print(f"[MON] row[{i}] sym_raw={_field(r,'asset_type','asset','symbol','base','ticker','asset_symbol')} sym_norm={_symbol_of(r)}")

    # Liquid (per-asset, normalized)
    liq_map, liq_src = resolve_liquid_thresholds(cfg)
    liq_vals = _liquid_values_from_positions(positions, dl) # {"SOL": 5.4, ...}
    if DEBUG_MONITOR_PANEL:
        print(f"[MON] liquid thresholds: {liq_map} src={liq_src}")
        print(f"[MON] liquid values (derived): {liq_vals}")

    symbols  = set(k for k, val in liq_map.items() if val is not None)
    symbols |= set(sym for sym in liq_vals.keys() if sym)
    if not symbols:
        symbols = set(_norm_sym(s) for s in FALLBACK_SYMBOLS)

    for sym in sorted(s for s in symbols if s):
        t = liq_map.get(sym)
        v = liq_vals.get(sym)
        outcome = NO_BREACH
        if _to_float(v) is not None and _to_float(t) is not None:
            outcome = BREACH if float(v) <= float(t) else NO_BREACH
        rows_out.append((
            f"{ICON_LIQUID} Liquid ({sym})",
            _fmt_num(v),
            _fmt_num(t),
            liq_src,
            outcome
        ))

    # Profit
    prof_single, prof_portf, profit_src = resolve_profit_thresholds(cfg)
    prof_thr = {"single": prof_single, "portfolio": prof_portf}
    prof_vals = _profit_values_from_positions(positions)    # {"single":v, "portfolio":v}
    if DEBUG_MONITOR_PANEL:
        print(f"[MON] profit thresholds (JSON): {prof_thr} src={profit_src}")
        print(f"[MON] profit values (derived): {prof_vals}")

    labels = {
        "single":    f"{ICON_PROFIT} Profit (Single)",
        "portfolio": f"{ICON_PROFIT} Profit (Portfolio)",
    }
    for key, label in labels.items():
        t = prof_thr.get(key)
        v = prof_vals.get(key)
        outcome = NO_BREACH
        if _to_float(v) is not None and _to_float(t) is not None:
            outcome = BREACH if float(v) >= float(t) else NO_BREACH
        rows_out.append((
            label,
            _fmt_money(v),
            _fmt_money(t),
            profit_src,
            outcome
        ))

    return rows_out


# ───────────────────────── rendering ─────────────────────────

def _render_plain(rows: List[Tuple[str, str, str, str, str]]) -> None:
    width = max(60, max((len("  ".join(r)) for r in rows), default=0))
    print(TITLE.center(width))
    print("─" * width)
    print("🧭 Monitor        📈 Value    🎯 Threshold    🗂 Source    🚦 Outcome")
    if not rows:
        print("(no rows)")
        return
    for m, v, t, s, o in rows:
        print(f"{m:<20} {v:<10} {t:<14} {s:<8} {o}")

def _render_rich(rows: List[Tuple[str, str, str, str, str]]) -> None:
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
    table.add_column("🧭 Monitor")
    table.add_column("📈 Value",     justify="right")
    table.add_column("🎯 Threshold",  justify="right")
    table.add_column("🗂 Source",     justify="center")
    table.add_column("🚦 Outcome",    justify="center")

    if not rows:
        table.add_row("(no rows)", "—", "—", "—", "—")
    else:
        for monitor, value, threshold, source, outcome in rows:
            outcome_text = "[bold red]BREACH[/]" if outcome == BREACH else "[green]no breach[/]"
            src_label = source or "EMPTY"
            if src_label == "EMPTY":
                src_text = "[dim]EMPTY[/]"
            else:
                src_text = f"[cyan]{src_label}[/]"
            table.add_row(monitor, value, threshold, src_text, outcome_text)

    meas = Measurement.get(console, console.options, table)
    table_width = max(60, meas.maximum)

    console.print(Text(TITLE.center(table_width), style=f"bold {TITLE_COLOR}"))
    console.print(Text("─" * table_width, style=RULE_COLOR))
    console.print(table)


# ───────────────────────── panel entry ─────────────────────────

def render(dl, _cycle_snapshot_unused, default_json_path=None):
    """
    Thresholds (JSON) + Values (positions + price fallback). No snapshot dependency.
    """
    cfg = _load_config(default_json_path)
    rows = _build_rows_from_json_and_positions(dl, cfg)
    _render_rich(rows)
