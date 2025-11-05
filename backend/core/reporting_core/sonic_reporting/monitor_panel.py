# -*- coding: utf-8 -*-
from __future__ import annotations
"""
monitor_panel — Monitors table (Liquid & Profit)

Contract (sequencer):
  render(dl, cycle_snapshot_unused, default_json_path=None)

Rules:
- Thresholds: read ONLY from JSON config (default_json_path or backend/config/sonic_monitor_config.json)
- Values:     read ONLY from positions via DataLocker -> dl.read_positions()
- Liquid breach  : value > threshold
- Profit breach  : value >= threshold
- Source column  : always "JSON" (threshold provenance)
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple
from pathlib import Path
import json
import os
import math

TITLE = "🧭 Monitors"
TITLE_COLOR = "bright_cyan"
RULE_COLOR  = "bright_cyan"

ICON_LIQUID = "💧"
ICON_PROFIT = "💵"

BREACH    = "BREACH"
NO_BREACH = "no breach"

DEFAULT_CONFIG_PATH = Path("backend/config/sonic_monitor_config.json")
FALLBACK_SYMBOLS = ("BTC", "ETH", "SOL")


# ───────────────────────── utils ─────────────────────────

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

def _is_liquid_breach(v: Any, t: Any) -> bool:
    fv, ft = _to_float(v), _to_float(t)
    return False if (fv is None or ft is None) else (fv > ft)

def _is_profit_breach(v: Any, t: Any) -> bool:
    fv, ft = _to_float(v), _to_float(t)
    return False if (fv is None or ft is None) else (fv >= ft)

def _load_config(default_json_path: Optional[str | os.PathLike]) -> Dict[str, Any]:
    path = Path(default_json_path) if default_json_path else DEFAULT_CONFIG_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# ───────────────────────── config readers (thresholds) ─────────────────────────

def _read_liquid_thresholds(cfg: Dict[str, Any]) -> Dict[str, float]:
    """
    JSON:
      liquid.thresholds: { "BTC": 5.3, "ETH": 111.0, "SOL": 21.5 }
    """
    try:
        t = cfg.get("liquid", {}).get("thresholds", {})
        if isinstance(t, dict):
            return {k.upper(): float(v) for k, v in t.items()}
    except Exception:
        pass
    return {}

def _read_profit_thresholds(cfg: Dict[str, Any]) -> Dict[str, float]:
    """
    JSON:
      profit.position_usd   -> "single"
      profit.portfolio_usd  -> "portfolio"
    """
    out: Dict[str, float] = {}
    p = cfg.get("profit", {}) if isinstance(cfg, dict) else {}
    try:
        if p.get("position_usd") is not None:
            out["single"] = float(p["position_usd"])
        if p.get("portfolio_usd") is not None:
            out["portfolio"] = float(p["portfolio_usd"])
    except Exception:
        pass
    return out


# ───────────────────────── DB readers (positions only) ─────────────────────────

def _read_positions(dl: Any) -> List[Dict[str, Any]]:
    """
    Expected to return an iterable of dict-like rows. We won't guess field names beyond a small
    tolerant set used in positions_panel: 'asset'/'symbol', 'pnl'/'unrealized_pnl', 'liq' or ('liq_price' & 'mark_price').
    """
    try:
        rows = dl.read_positions()
        if isinstance(rows, list):
            return rows
        # Some implementations return generators or tuples; normalize to list
        return list(rows)
    except Exception:
        return []

def _symbol_of(row: Dict[str, Any]) -> Optional[str]:
    for k in ("asset", "symbol", "base", "ticker"):
        v = row.get(k)
        if isinstance(v, str) and v:
            return v.upper()
    return None

def _pnl_of(row: Dict[str, Any]) -> Optional[float]:
    for k in ("pnl", "unrealized_pnl", "upnl", "pnl_usd"):
        v = row.get(k)
        if _to_float(v) is not None:
            return float(v)
    return None

def _liq_distance_pct_of(row: Dict[str, Any]) -> Optional[float]:
    """
    Try to recover 'distance to liquidation' in percent, consistent with what a monitor would care about.
    1) If a percent-like field exists (liq, liq_pct, dist_to_liq_pct), use it.
    2) Else compute from prices if present: |mark - liq_price| / mark * 100
    """
    for k in ("liq", "liq_pct", "dist_to_liq_pct", "distance_liq_pct"):
        if _to_float(row.get(k)) is not None:
            return float(row[k])

    liq_price = row.get("liq_price") or row.get("liquidation_price")
    mark      = row.get("mark_price") or row.get("price") or row.get("current_price")
    if _to_float(liq_price) is not None and _to_float(mark) is not None and float(mark) != 0:
        return abs((float(mark) - float(liq_price)) / float(mark)) * 100.0

    return None


# ───────────────────────── aggregation (values from positions) ─────────────────────────

def _liquid_values_from_positions(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    For each symbol, take the *worst* (smallest) distance-to-liquidation across positions in that symbol.
    Rationale: monitor should warn on the closest-to-liquidation leg.
    """
    best: Dict[str, float] = {}
    for r in rows:
        sym = _symbol_of(r)
        if not sym:
            continue
        d = _liq_distance_pct_of(r)
        if d is None:
            continue
        # keep the minimal distance (worst-case)
        if sym not in best or d < best[sym]:
            best[sym] = d
    return best

def _profit_values_from_positions(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    'single'    : max positive PnL across positions (0 if none positive)
    'portfolio' : net sum PnL across positions
    """
    max_pos = 0.0
    total   = 0.0
    for r in rows:
        p = _pnl_of(r)
        if p is None:
            continue
        total += p
        if p > max_pos:
            max_pos = p
    return {"single": max_pos, "portfolio": total}


# ───────────────────────── row assembly ─────────────────────────

def _build_rows_from_json_and_positions(
    dl: Any,
    cfg: Dict[str, Any],
) -> List[Tuple[str, str, str, str, str]]:
    """
    Compose rows using:
      • thresholds from JSON config (source='JSON')
      • values derived from dl.read_positions()
    """
    rows_out: List[Tuple[str, str, str, str, str]] = []

    positions = _read_positions(dl)

    # Liquid
    liq_thr = _read_liquid_thresholds(cfg)              # per-symbol thresholds
    liq_vals = _liquid_values_from_positions(positions) # per-symbol values
    # Decide which symbols to show: any symbol that has a threshold, or appears in positions
    symbols = set(liq_thr.keys()) | set(liq_vals.keys()) or set(FALLBACK_SYMBOLS)
    for sym in sorted(symbols):
        t = liq_thr.get(sym)
        v = liq_vals.get(sym)
        # Show only if we have both a threshold and a computable value
        if t is None or v is None:
            continue
        rows_out.append((
            f"{ICON_LIQUID} Liquid ({sym})",
            _fmt_num(v),
            _fmt_num(t),
            "JSON",
            BREACH if _is_liquid_breach(v, t) else NO_BREACH
        ))

    # Profit
    prof_thr = _read_profit_thresholds(cfg)             # {"single": x, "portfolio": y}
    prof_vals = _profit_values_from_positions(positions)# {"single": v, "portfolio": v}
    labels = {
        "single":    f"{ICON_PROFIT} Profit (Single)",
        "portfolio": f"{ICON_PROFIT} Profit (Portfolio)",
    }
    for key, label in labels.items():
        t = prof_thr.get(key)
        v = prof_vals.get(key)
        if t is None or v is None:
            continue
        rows_out.append((
            label,
            _fmt_money(v),
            _fmt_money(t),
            "JSON",
            BREACH if _is_profit_breach(v, t) else NO_BREACH
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
            src_text = "[cyan]JSON[/]"  # thresholds provenance for this panel
            table.add_row(monitor, value, threshold, src_text, outcome_text)

    meas = Measurement.get(console, console.options, table)
    table_width = max(60, meas.maximum)

    console.print(Text(TITLE.center(table_width), style=f"bold {TITLE_COLOR}"))
    console.print(Text("─" * table_width, style=RULE_COLOR))
    console.print(table)


# ───────────────────────── panel entry ─────────────────────────

def render(dl, _cycle_snapshot_unused, default_json_path=None):
    """
    Thresholds (JSON) + Values (positions only). No snapshot dependency.
    """
    cfg = _load_config(default_json_path)
    rows = _build_rows_from_json_and_positions(dl, cfg)
    _render_rich(rows)
