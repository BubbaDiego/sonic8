# -*- coding: utf-8 -*-
from __future__ import annotations
"""
monitor_panel — Monitors table: Liquid & Profit + Source column

Contract (sequencer):
  render(dl, csum, default_json_path=None)

UI:
- Centered title + cyan rule
- Rich table (SIMPLE_HEAD)
- No separator between groups
- Header icons: 🧭 / 📈 / 🎯 / 🗂 / 🚦
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple

TITLE = "🧭 Monitors"
TITLE_COLOR = "bright_cyan"
RULE_COLOR  = "bright_cyan"

ICON_LIQUID = "💧"
ICON_PROFIT = "💵"

BREACH    = "BREACH"
NO_BREACH = "no breach"

FALLBACK_SYMBOLS = ("BTC", "ETH", "SOL")

# ───────────────────────── number/label formatting ─────────────────────────

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

def _src_label(x: Any) -> str:
    if x is None: return "—"
    s = str(x).strip().lower()
    if s in {"json", "file", "config", "cfg"} or "file" in s or "json" in s or "config" in s:
        return "JSON"
    if s in {"db", "database", "sql"} or "db" in s or "sql" in s:
        return "DB"
    return "—"

# ───────────────────────── breach rules ─────────────────────────

def _is_liquid_breach(v: Any, t: Any) -> bool:
    fv, ft = _to_float(v), _to_float(t)
    return False if (fv is None or ft is None) else (fv > ft)

def _is_profit_breach(v: Any, t: Any) -> bool:
    fv, ft = _to_float(v), _to_float(t)
    return False if (fv is None or ft is None) else (fv >= ft)

# ───────────────────────── csum harvesting ─────────────────────────

def _from_csum(csum: Optional[Dict[str, Any]]) -> List[Tuple[str, str, str, str, str]]:
    rows: List[Tuple[str, str, str, str, str]] = []
    if not isinstance(csum, dict):
        return rows
    monitors = csum.get("monitors")
    if not isinstance(monitors, dict):
        return rows

    # Liquid
    liquid = monitors.get("liquid")
    if isinstance(liquid, dict):
        for sym, d in liquid.items():
            if not isinstance(d, dict): continue
            v = d.get("value"); t = d.get("threshold")
            src = d.get("source") or d.get("provenance") or d.get("origin")
            b = bool(d.get("breach", _is_liquid_breach(v, t)))
            rows.append((f"{ICON_LIQUID} Liquid ({sym})", _fmt_num(v), _fmt_num(t), _src_label(src), BREACH if b else NO_BREACH))

    # Profit
    profit = monitors.get("profit")
    if isinstance(profit, dict):
        for key, label in [("single", f"{ICON_PROFIT} Profit (Single)"),
                           ("portfolio", f"{ICON_PROFIT} Profit (Portfolio)")]:
            d = profit.get(key)
            if not isinstance(d, dict): continue
            v = d.get("value"); t = d.get("threshold")
            src = d.get("source") or d.get("provenance") or d.get("origin")
            b = bool(d.get("breach", _is_profit_breach(v, t)))
            rows.append((label, _fmt_money(v), _fmt_money(t), _src_label(src), BREACH if b else NO_BREACH))
    return rows

# ───────────────────────── DataLocker harvesting ─────────────────────────

def _safe_getattr(obj: Any, name: str, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default

def _probe_dl_threshold_source(dl: Any, monitor: str, key: str) -> str:
    fn = _safe_getattr(dl, "get_threshold_source", None)
    if callable(fn):
        try:
            return _src_label(fn(monitor, key))
        except Exception:
            pass

    for attr in ("threshold_provenance", "monitor_provenance", "monitor_sources",
                 "liquid_thresholds_source", "profit_thresholds_source"):
        pv = _safe_getattr(dl, attr, None)
        if isinstance(pv, dict):
            if monitor in pv and isinstance(pv[monitor], dict) and key in pv[monitor]:
                return _src_label(pv[monitor][key])
            if key in pv:
                return _src_label(pv[key])

    flat = f"{monitor}_{key}_thresh_source".replace("liquid_", "").replace("profit_", "profit_")
    src = _safe_getattr(dl, flat, None)
    if src is not None:
        return _src_label(src)

    mode = _safe_getattr(dl, "config_mode", None)
    if isinstance(mode, str) and mode.strip().upper().startswith("JSON"):
        return "JSON"
    return "—"

def _from_dl_dicts(dl: Any) -> List[Tuple[str, str, str, str, str]]:
    rows: List[Tuple[str, str, str, str, str]] = []
    for attr in ("monitors", "monitor_summary", "monitor_snapshot", "monitor_results", "monitor_state"):
        md = _safe_getattr(dl, attr, None)
        if not isinstance(md, dict):
            continue

        liq = md.get("liquid")
        if isinstance(liq, dict):
            for sym, d in liq.items():
                if not isinstance(d, dict): continue
                v, t = d.get("value"), d.get("threshold")
                if v is None or t is None: continue
                src = d.get("source") or d.get("provenance") or d.get("origin") or _probe_dl_threshold_source(dl, "liquid", str(sym))
                rows.append((f"{ICON_LIQUID} Liquid ({sym})", _fmt_num(v), _fmt_num(t), _src_label(src), BREACH if _is_liquid_breach(v, t) else NO_BREACH))

        prof = md.get("profit")
        if isinstance(prof, dict):
            for key, label in [("single", f"{ICON_PROFIT} Profit (Single)"),
                               ("portfolio", f"{ICON_PROFIT} Profit (Portfolio)")]:
                d = prof.get(key)
                if not isinstance(d, dict): continue
                v, t = d.get("value"), d.get("threshold")
                if v is None or t is None: continue
                src = d.get("source") or d.get("provenance") or d.get("origin") or _probe_dl_threshold_source(dl, "profit", key)
                rows.append((label, _fmt_money(v), _fmt_money(t), _src_label(src), BREACH if _is_profit_breach(v, t) else NO_BREACH))
    return rows

def _from_dl_pairs(dl: Any) -> List[Tuple[str, str, str, str, str]]:
    rows: List[Tuple[str, str, str, str, str]] = []

    liquid_values  = _safe_getattr(dl, "liquid_values", None) or {}
    liquid_thresh  = _safe_getattr(dl, "liquid_thresholds", None) or {}
    has_liquid     = isinstance(liquid_values, dict) or isinstance(liquid_thresh, dict)

    if has_liquid:
        syms: Iterable[str] = set(liquid_values.keys()) | set(liquid_thresh.keys()) or set(FALLBACK_SYMBOLS)
        for sym in syms:
            v = liquid_values.get(sym) if isinstance(liquid_values, dict) else None
            t = liquid_thresh.get(sym) if isinstance(liquid_thresh, dict) else None
            if v is None:
                gv = _safe_getattr(dl, "get_liquid_value", None)
                if callable(gv):
                    try: v = gv(sym)
                    except Exception: pass
            if t is None:
                gt = _safe_getattr(dl, "get_liquid_threshold", None)
                if callable(gt):
                    try: t = gt(sym)
                    except Exception: pass
            if v is None or t is None:
                continue
            src = _probe_dl_threshold_source(dl, "liquid", str(sym))
            rows.append((f"{ICON_LIQUID} Liquid ({sym})", _fmt_num(v), _fmt_num(t), _src_label(src), BREACH if _is_liquid_breach(v, t) else NO_BREACH))

    psv  = _safe_getattr(dl, "profit_single_value",  None)
    pst  = _safe_getattr(dl, "profit_single_thresh", None)
    if psv is not None and pst is not None:
        src = _safe_getattr(dl, "profit_single_thresh_source", None) or _probe_dl_threshold_source(dl, "profit", "single")
        rows.append((f"{ICON_PROFIT} Profit (Single)", _fmt_money(psv), _fmt_money(pst), _src_label(src), BREACH if _is_profit_breach(psv, pst) else NO_BREACH))

    ppv  = _safe_getattr(dl, "profit_portfolio_value",  None)
    ppt  = _safe_getattr(dl, "profit_portfolio_thresh", None)
    if ppv is not None and ppt is not None:
        src = _safe_getattr(dl, "profit_portfolio_thresh_source", None) or _probe_dl_threshold_source(dl, "profit", "portfolio")
        rows.append((f"{ICON_PROFIT} Profit (Portfolio)", _fmt_money(ppv), _fmt_money(ppt), _src_label(src), BREACH if _is_profit_breach(ppv, ppt) else NO_BREACH))

    return rows

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
            src_text = "[cyan]JSON[/]" if source == "JSON" else ("[magenta]DB[/]" if source == "DB" else "—")
            table.add_row(monitor, value, threshold, src_text, outcome_text)

    # Proper width measurement (does not print)
    meas = Measurement.get(console, console.options, table)
    table_width = max(60, meas.maximum)

    console.print(Text(TITLE.center(table_width), style=f"bold {TITLE_COLOR}"))
    console.print(Text("─" * table_width, style=RULE_COLOR))
    console.print(table)

# ───────────────────────── panel entry ─────────────────────────

def render(dl, csum, default_json_path=None):
    rows = _from_csum(csum)
    if not rows:
        rows = _from_dl_dicts(dl) or _from_dl_pairs(dl) or []
    _render_rich(rows)
