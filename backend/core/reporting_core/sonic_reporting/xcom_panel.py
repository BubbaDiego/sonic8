# -*- coding: utf-8 -*-
from __future__ import annotations
"""
xcom_panel — DL-sourced XCOM status, Rich-styled like sync_panel (NO rising-edge)

Panel-local options (tweak here; no sequencer change needed):
  XCOM_BORDER  = "light" | "none"       # bordered Rich table or plain list
  TITLE_COLOR  = <rich color>           # title color (e.g., "bright_cyan")
  BORDER_COLOR = <rich color>           # border color (e.g., "bright_black")

Contract (lean sequencer):
  render(dl, csum, default_json_path=None)

Notes:
  • Reads JSON via config_probe (monitor-level), not csum.
  • Uses DataLocker + DLPositionManager so the panel sees what monitors/UI see.
  • Prints each gate explicitly: breach, channel.voice, xcom_ready, cooldown, snooze.
  • No rising-edge logic in this panel.

Source reference: :contentReference[oaicite:0]{index=0}
"""

from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timezone

# Data source + logging
from backend.data.data_locker import DataLocker
from backend.data.dl_positions import DLPositionManager
from backend.core.logging import log

# Config probe (present in repo)
from backend.core.reporting_core.sonic_reporting.config_probe import (
    discover_json_path,
    parse_json,
)

# Monitor-level notifications resolver
from backend.core.xcom_core.xcom_config_service import XComConfigService

# Provider gates
from backend.core.reporting_core.sonic_reporting.xcom_extras import (
    xcom_ready,
    read_voice_cooldown_remaining,
    xcom_live_status,
)

# ───────────────────── Panel-local UI options ─────────────────────
XCOM_BORDER  = "light"         # "light" | "none"
TITLE_COLOR  = "bright_cyan"   # Rich color name
BORDER_COLOR = "bright_black"  # Rich color name
# ──────────────────────────────────────────────────────────────────


_IC = {"ok": "✅", "skip": "⏭", "phone": "📞", "sys": "🖥️", "tts": "🔊", "sms": "💬"}

def _tick(b: bool) -> str:
    return _IC["ok"] if b else _IC["skip"]

def _ensure_dl(dl: Optional[DataLocker]) -> DataLocker:
    if dl is not None:
        return dl
    try:
        return DataLocker.get_instance(r"C:\sonic7\backend\mother.db")
    except Exception:
        return DataLocker.get_instance()

# ---------------- JSON + channels ----------------

def _cfg_from(dl: DataLocker, default_json_path: Optional[str]) -> Tuple[dict, str]:
    """FILE → RUNTIME → EMPTY (mirror of sync panel’s behavior)."""
    # FILE (explicit)
    if default_json_path:
        try:
            cfg_obj, err, meta = parse_json(default_json_path)
            if isinstance(cfg_obj, dict) and cfg_obj:
                return cfg_obj, f"FILE {default_json_path}"
        except Exception as e:
            print(f"[XCOM] cfg file error: {e}")

    # RUNTIME
    if isinstance(getattr(dl, "global_config", None), dict) and dl.global_config:
        return dl.global_config, "RUNTIME —"

    # Discover FILE
    try:
        p = discover_json_path(None)
        if p:
            cfg_obj, err, meta = parse_json(p)
            if isinstance(cfg_obj, dict) and cfg_obj:
                return cfg_obj, f"FILE {p}"
    except Exception as e:
        print(f"[XCOM] cfg discover error: {e}")

    return {}, "EMPTY —"


def _thresholds(cfg: dict) -> Dict[str, Optional[float]]:
    """
    Prefer 'liquid_monitor.thresholds', then 'liquid.thresholds'.
    Returns {'BTC': float|None, 'ETH': ..., 'SOL': ...}
    """
    block = {}
    try:
        block = (cfg.get("liquid_monitor") or {}).get("thresholds") or {}
        if not block:
            block = (cfg.get("liquid") or {}).get("thresholds") or {}
    except Exception:
        block = {}
    out: Dict[str, Optional[float]] = {}
    for k in ("BTC", "ETH", "SOL"):
        try:
            out[k] = float(block.get(k)) if k in block else None
        except Exception:
            out[k] = None
    return out


def _channels(cfg: dict, dl: DataLocker) -> Dict[str, bool]:
    """Monitor-level notifications (no global channel gate)."""
    try:
        svc = XComConfigService(getattr(dl, "system", None), config=cfg)
        ch = svc.channels_for("liquid") or {}
        return {
            "voice": bool(ch.get("voice", False)),
            "system": bool(ch.get("system", False)),
            "sms": bool(ch.get("sms", False)),
            "tts": bool(ch.get("tts", False)),
        }
    except Exception as e:
        print(f"[XCOM] channels error: {e}")
        return {"voice": False, "system": False, "sms": False, "tts": False}

# ---------------- Breaches from DL ----------------

def _active_breaches(dl: DataLocker, thr: Dict[str, Optional[float]]) -> List[dict]:
    """
    Compute live breaches from active positions (value ≤ threshold).
    We take the MIN(liq_distance) per asset among active rows.
    """
    out: List[dict] = []
    try:
        mgr = DLPositionManager(dl.db)
        rows = mgr.get_active_positions() or []
    except Exception as e:
        print(f"[XCOM] positions error: {e}")
        rows = []

    mins: Dict[str, float] = {}
    for p in rows:
        try:
            sym = str(getattr(p, "asset_type", "") or "").upper()
            if not sym:
                continue
            dist = None
            for k in ("liquidation_distance", "liquidation", "liq", "liq_dist", "liq_pct"):
                v = getattr(p, k, None)
                if v is None:
                    continue
                try:
                    dist = float(v)
                    break
                except Exception:
                    pass
            if dist is None:
                continue
            prev = mins.get(sym)
            if prev is None or dist < prev:
                mins[sym] = dist
        except Exception:
            continue

    for sym, v in mins.items():
        t = thr.get(sym)
        if t is None:
            continue
        if v <= t:
            out.append({"asset": sym, "value": v, "threshold": float(t)})
    return out

# ---------------- Snooze ----------------

def _snooze_ok(dl: DataLocker) -> bool:
    """
    Snooze via dl.system['liquid_monitor']:
      {"snooze_seconds": int, "_last_alert_ts": epoch-seconds}
    Return True when NOT snoozed (ok to call).
    """
    try:
        rec = dl.system.get_var("liquid_monitor") or {}
        snooze_sec = int(rec.get("snooze_seconds") or 0)
        last_ts = float(rec.get("_last_alert_ts") or 0)
        if snooze_sec <= 0 or last_ts <= 0:
            return True
        now = datetime.now(timezone.utc).timestamp()
        return (now - last_ts) >= snooze_sec
    except Exception:
        return True

# ---------------- Rendering ----------------

def _render_bordered(rows: List[List[str]], header: List[str], title: str) -> None:
    try:
        from rich.table import Table
        from rich.console import Console
        from rich.box import SIMPLE
    except Exception:
        _render_unbordered(rows, header, title)
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


def _render_unbordered(rows: List[List[str]], header: List[str], title: str) -> None:
    print(f"\n  {title}\n")
    widths = [max(len(str(header[c])), max(len(str(r[c])) for r in rows) if rows else 0)
              for c in range(len(header))]
    print("  " + "  ".join(str(header[c]).ljust(widths[c]) for c in range(len(header))))
    print("")
    for r in rows:
        print("  " + "  ".join(str(r[c]).ljust(widths[c]) for c in range(len(header))))

# ---------------- Panel entry ----------------

def render(dl: Optional[DataLocker], csum: Optional[dict], default_json_path: Optional[str] = None) -> None:
    """
    DL + JSON + gate matrix in a Rich-styled table (no rising-edge).
    """
    dl = _ensure_dl(dl)

    # Config + channels
    cfg, cfg_src = _cfg_from(dl, default_json_path)
    ch = _channels(cfg, dl)

    # Provider gates
    try:
        ready_ok, ready_reason = xcom_ready(dl, cfg=cfg)
    except Exception as e:
        ready_ok, ready_reason = False, f"ready-error({e})"

    try:
        rem_s, _ = read_voice_cooldown_remaining(dl)
        cooldown_ok = (rem_s <= 0)
    except Exception:
        rem_s, cooldown_ok = 0, True

    try:
        live_on, live_src = xcom_live_status(dl, cfg=getattr(dl, "global_config", None))
    except Exception:
        live_on, live_src = False, "—"

    # Thresholds + breaches
    thr = _thresholds(cfg)
    breaches = _active_breaches(dl, thr)

    # Snooze
    snooze_ok = _snooze_ok(dl)

    # Prepare rows
    header = ["Check", "Status", "Details"]
    rows: List[List[str]] = []

    # Top summary
    rows.append(["cfg source", _tick(cfg != {}), cfg_src])
    rows.append(["XCOM live", _ok_label(live_on := bool(live_on := live_on)), f"[{live_src}]"])
    rows.append([
        "channels(liquid)",
        _tick(any(ch.values())),
        f"{_IC['phone']} {_tick(ch.get('voice', False))}  "
        f"{_IC['sys']} {_tick(ch.get('system', False))}  "
        f"{_IC['tts']} {_tick(ch.get('tts', False))}  "
        f"{_IC['sms']} {_tick(ch.get('sms', False))}"
    ])
    rows.append(["provider cooldown", _tick(cooldown_ok), "idle" if cooldown_ok else f"{int(rem_s)}s"])

    # Breaches summary
    if breaches:
        rows.append(["breaches", _tick(True), f"{len(breaches)}"])
        for b in breaches:
            rows.append([f" • {b['asset']}", "—", f"{b['value']:.2f} ≤ {b['threshold']:.2f}"])
    else:
        rows.append(["breaches", _tick(False), "0"])

    # Gate matrix (no rising-edge here)
    rows.append(["breach", _tick(bool(breaches)), "—"])
    rows.append(["channel.voice", _tick(ch.get('voice', False)), "—"])
    rows.append(["xcom_ready", _tick(ready_ok), ("ok" if ready_ok else str(ready_reason))])
    rows.append(["provider_cooldown_ok", _tick(cooldown_ok), "—"])
    rows.append(["monitor_snoozed=False", _tick(snooze_ok), "—"])

    title = "🔍 XCOM Check"

    if XCOM_BORDER == "light":
        _render_bordered(rows, header, title)
    else:
        _render_unbordered(rows, header, title)

    # Breadcrumb (useful when diagnosing)
    print(f"\n[XCOM] source: cfg={cfg_src}  breaches={len(breaches)}")

def _ok_label(ok: bool) -> str:
    return "🟢 ON" if ok else "🔴 OFF"
