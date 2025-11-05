# -*- coding: utf-8 -*-
from __future__ import annotations

"""
sync_panel — Sonic Monitor configuration / health (Rich table + options)

Panel-local options (tweak here, no sequencer changes required):
  SYNC_BORDER   : "light" | "none"     # bordered Rich table or plain list
  TITLE_COLOR   : Rich color name      # title text color
  BORDER_COLOR  : Rich color name      # border color

Signature (matches the lean sequencer):
  render(dl, csum, default_json_path=None)
"""

from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timezone

# Data/infra
from backend.data.data_locker import DataLocker
from backend.core.logging import log

# Config helpers
from backend.core.reporting_core.sonic_reporting.config_probe import (
    discover_json_path,
    parse_json,
)

# XCOM gate helpers
from backend.core.reporting_core.sonic_reporting.xcom_extras import (
    xcom_live_status,
    read_voice_cooldown_remaining,
)

# ───────────────────────────────── Panel-local render options ─────────────────────────────────
SYNC_BORDER   = "light"           # "light" | "none"
TITLE_COLOR   = "bright_cyan"     # Rich color, e.g., "cyan", "bright_white"
BORDER_COLOR  = "bright_black"    # Rich color, e.g., "white", "bright_black"
# ─────────────────────────────────────────────────────────────────────────────────────────────


# ────────────────────────────────── Utilities ──────────────────────────────────

def _tick(ok: bool) -> str:
    return "✅" if ok else "❌"

def _ok_label(ok: bool) -> str:
    return "🟢 ON" if ok else "🔴 OFF"

def _ensure_dl(dl: Optional[DataLocker]) -> DataLocker:
    if dl is not None:
        return dl
    try:
        return DataLocker.get_instance(r"C:\sonic7\backend\mother.db")
    except Exception:
        return DataLocker.get_instance()

def _safe_get(d: Dict[str, Any], path: List[str], default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def _snooze_label(dl: DataLocker) -> str:
    try:
        rec = dl.system.get_var("liquid_monitor") or {}
        sec = int(rec.get("snooze_seconds") or 0)
        return "disabled" if sec <= 0 else f"{sec}s"
    except Exception:
        return "—"

def _cooldown_label(dl: DataLocker) -> Tuple[str, str]:
    try:
        rem_s, src = read_voice_cooldown_remaining(dl)
        return ("idle" if rem_s <= 0 else f"{int(rem_s)}s", src or "")
    except Exception:
        return ("idle", "")

def _schema_markers(cfg: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Return (ok, 8 markers) where markers are 'name ✓' or 'name —'.
    We show them in two rows with 4 items each.
    """
    sections = ["monitor", "channels", "liquid", "profit", "market", "price", "liquid_monitor", "profit_monitor"]
    ok = True
    marks: List[str] = []
    for s in sections:
        present = s in cfg
        marks.append(f"{s} {'✓' if present else '—'}")
        ok = ok and present
    return ok, marks

def _liquid_thresholds(cfg: Dict[str, Any]) -> Dict[str, Optional[float]]:
    block = _safe_get(cfg, ["liquid", "thresholds"], None) or _safe_get(cfg, ["liquid_monitor", "thresholds"], {})
    out: Dict[str, Optional[float]] = {}
    for k in ("BTC", "ETH", "SOL"):
        try:
            out[k] = float(block.get(k)) if block and k in block else None
        except Exception:
            out[k] = None
    return out

def _profit_thresholds(cfg: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    single = _safe_get(cfg, ["profit", "position_profit_usd"])
    portfolio = _safe_get(cfg, ["profit", "portfolio_profit_usd"])
    if single is None:
        single = _safe_get(cfg, ["profit", "position_usd"])
    if portfolio is None:
        portfolio = _safe_get(cfg, ["profit", "portfolio_usd"])
    try:
        single = float(single) if single is not None else None
    except Exception:
        single = None
    try:
        portfolio = float(portfolio) if portfolio is not None else None
    except Exception:
        portfolio = None
    return single, portfolio


# ────────────────────────────────── Rendering ──────────────────────────────────

def _render_bordered(rows: List[List[str]], header: List[str], title: str) -> None:
    # Rich is “fancy third-party”; fall back if not available
    try:
        from rich.table import Table
        from rich.console import Console
        from rich.box import SIMPLE, SQUARE, HEAVY, MINIMAL
    except Exception:
        _render_unbordered(rows, header, title)
        return

    console = Console()
    # choose a light box style
    border_style = BORDER_COLOR
    table = Table(
        title=f"[{TITLE_COLOR}]{title}[/{TITLE_COLOR}]",
        show_header=True,
        box=SIMPLE,
        border_style=border_style,
        title_justify="left",
        header_style="bold",
        show_edge=True,
        show_lines=False,
        expand=False,
        pad_edge=False,
    )
    for col in header:
        table.add_column(col)

    for r in rows:
        table.add_row(*[str(c) for c in r])

    console.print(table)


def _render_unbordered(rows: List[List[str]], header: List[str], title: str) -> None:
    print(f"\n  {title}\n")
    # compute widths
    widths = [max(len(str(header[c])), max(len(str(r[c])) for r in rows) if rows else 0) for c in range(len(header))]
    print("  " + "  ".join(str(header[c]).ljust(widths[c]) for c in range(len(header))))
    print("")
    for r in rows:
        print("  " + "  ".join(str(r[c]).ljust(widths[c]) for c in range(len(header))))


# ────────────────────────────────── Panel entry ──────────────────────────────────

def render(dl: Optional[DataLocker], csum: Optional[dict], default_json_path: Optional[str] = None) -> None:
    dl = _ensure_dl(dl)

    # 1) XCOM live
    try:
        live_on, live_src = xcom_live_status(dl, cfg=getattr(dl, "global_config", None))
    except Exception:
        live_on, live_src = False, "—"

    # 2) JSON path + load (we do not print the “Parse JSON” line anymore)
    cfg = {}
    cfg_src = "—"
    try:
        path = default_json_path or discover_json_path(None)
        if path:
            cfg_obj, err, meta = parse_json(path)
            if isinstance(cfg_obj, dict) and cfg_obj:
                cfg = cfg_obj
                cfg_src = path
    except Exception as e:
        # Keep cfg empty; rows below will reflect that.
        log.debug("sync_panel: JSON parse error", source="sync_panel", payload={"error": str(e)})

    # 3) Loop interval, snooze, cooldown
    loop_secs = _safe_get(cfg, ["monitor", "loop_seconds"], None)
    snooze = _snooze_label(dl)
    cd_label, _ = _cooldown_label(dl)

    # 4) Schema check split into two lines (4 markers per row)
    sch_ok, markers = _schema_markers(cfg)
    # Guarantee 8 items
    while len(markers) < 8:
        markers.append("—")
    row_a = " · ".join(markers[0:4])
    row_b = " · ".join(markers[4:8])

    # 5) Thresholds
    lq = _liquid_thresholds(cfg) if cfg else {"BTC": None, "ETH": None, "SOL": None}
    pf_s, pf_p = _profit_thresholds(cfg) if cfg else (None, None)

    header = ["Activity", "Status", "Details"]
    rows: List[List[str]] = []

    rows.append(["🛰 XCOM Live", _ok_label(live_on), f"[{live_src}]"])
    rows.append(["⏱ Loop interval", _tick(loop_secs is not None), f"{loop_secs or '—'}s • Runtime · live loop"])
    rows.append(["🔕 Alert snooze", _tick(True), snooze])
    rows.append(["🔔 Voice cooldown", _tick(cd_label == "idle"), f"{cd_label} • default 180s"])
    rows.append(["📦 Config JSON path", _tick(cfg_src != "—"), cfg_src])
    # (removed) rows.append(["🧪 Parse JSON", _tick(parse_ok), parse_detail])

    rows.append(["🔎 Schema check (1/2)", _tick(sch_ok), row_a])
    rows.append(["🔎 Schema check (2/2)", _tick(sch_ok), row_b])

    rows.append(["🧭 Read monitor thresholds", _tick(True), "JSON→DB→ENV"])

    lt_detail = " • ".join([
        f"🟡 BTC {lq.get('BTC') if lq.get('BTC') is not None else '—'} (FILE)",
        f"🔷 ETH {lq.get('ETH') if lq.get('ETH') is not None else '—'} (FILE)",
        f"🟣 SOL {lq.get('SOL') if lq.get('SOL') is not None else '—'} (FILE)",
    ]) if cfg else "—"
    rows.append(["💧 Liquid thresholds", _tick(cfg != {}), lt_detail])

    pf_detail = " • ".join([
        f"👤 Single ${pf_s:.0f} (FILE)" if pf_s is not None else "👤 Single —",
        f"🧺 Portfolio ${pf_p:.0f} (FILE)" if pf_p is not None else "🧺 Portfolio —",
    ]) if cfg else "—"
    rows.append(["💵 Profit thresholds", _tick(cfg != {}), pf_detail])

    title = "🧪 Sonic Monitor Configuration"

    if SYNC_BORDER == "light":
        _render_bordered(rows, header, title)
    else:
        _render_unbordered(rows, header, title)

    # Breadcrumb
    print(f"\n[SEQ] ok: backend.core.reporting_core.sonic_reporting.sync_panel")
