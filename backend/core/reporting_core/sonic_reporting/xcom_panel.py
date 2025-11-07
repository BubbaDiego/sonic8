# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Optional, Dict, List

from rich.console import Console
from rich.table import Table
from rich import box

# Canonical Alerts store — published breaches come from here
from backend.data import dl_alerts

# Config helpers (same as other panels)
try:
    from backend.core.reporting_core.sonic_reporting.config_probe import discover_json_path, parse_json
except Exception:
    def discover_json_path(_): return None
    def parse_json(_): return {}, None, {}

# Shared live-status resolver (same path as banner/sync)
try:
    from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_live_status
except Exception:
    def xcom_live_status(dl: Any, cfg: dict | None = None) -> tuple[bool, str]:
        v = getattr(dl, "xcom_live", None)
        return (bool(v), "RUNTIME") if isinstance(v, bool) else (False, "—")


# ---------- helpers ----------

def _cfg() -> tuple[dict, Optional[str]]:
    cfg = {}
    path = None
    try:
        path = discover_json_path(None)
        if path:
            obj, err, meta = parse_json(path)
            if isinstance(obj, dict):
                cfg = obj
    except Exception:
        cfg = {}
    return cfg, path

def _notif(cfg: Dict, key: str) -> Dict[str, bool]:
    node = cfg.get(key, {}) or cfg.get(f"{key}_monitor", {}) or {}
    n = node.get("notifications", {}) or {}
    return {
        "voice": bool(n.get("voice", True)),
        "system": bool(n.get("system", True)),
        "tts": bool(n.get("tts", True)),
        "sms": bool(n.get("sms", False)),
    }

def _icons_enabled(n: Dict[str, bool]) -> str:
    icons: List[str] = []
    if n["voice"]:  icons.append("📞")
    if n["system"]: icons.append("🖥️")
    if n["tts"]:    icons.append("🔊")
    if n["sms"]:    icons.append("💬")
    return " ".join(icons) if icons else "—"

def _snoozed(dl: Any) -> bool:
    for key in ("monitor_snoozed", "liquid_snoozed", "liquid_snooze"):
        v = getattr(dl, key, 0)
        try:
            if float(v) > 0: return True
        except Exception:
            if isinstance(v, bool) and v: return True
    return False

def _onoff(v: bool) -> str:
    return "[bold green]ON[/]" if v else "[bold red]OFF[/]"


# ---------- main render ----------

def render(dl: Any, csum: Optional[dict] = None) -> None:
    """
    XCOM panel styled like the Monitors panel:
      Item | Value | Source | Notes
    - left aligned columns
    - header-only frame (no outer border)
    - compact rows (no extra spacing)
    """
    console = Console()

    t = Table(
        title="🧭  XCOM",
        show_header=True,
        header_style="bold",
        box=box.SIMPLE_HEAD,       # header line only
        show_edge=False,
        show_lines=False,
        pad_edge=False,
        padding=(0, 1),            # compact rows
        expand=True,
    )

    # Left-justify + no-wrap so columns align tightly
    t.add_column("Item",   justify="left", no_wrap=True)
    t.add_column("Value",  justify="left", no_wrap=True)
    t.add_column("Source", justify="left", no_wrap=True)
    t.add_column("Notes",  justify="left", no_wrap=True)

    cfg, cfg_path = _cfg()

    # 1) cfg source
    t.add_row("🛠️  cfg source", "—", f"FILE {cfg_path}" if cfg_path else "[-]", "[-]")

    # 2) XCOM Live — put ON/OFF in Notes; Source shows resolver label
    live, live_src = xcom_live_status(dl, cfg=cfg or getattr(dl, "global_config", None))
    t.add_row("📡  XCOM Live", "—", f"[{live_src}]", _onoff(bool(live)))

    # 3) channels(liquid) — icons only if enabled
    n_liq = _notif(cfg, "liquid")
    t.add_row("🔔  channels(liquid)", _icons_enabled(n_liq), "JSON:liquid", "—")

    # 4) channels(profit) — icons only if enabled
    n_prof = _notif(cfg, "profit")
    t.add_row("💵  channels(profit)", _icons_enabled(n_prof), "JSON:profit", "—")

    # 5) breaches (published) — Alerts DB (open only)
    open_alerts = dl_alerts.list_open(dl, kind="breach", monitor="liquid")
    syms = ", ".join(sorted({(a.get("symbol") or "") for a in open_alerts if isinstance(a, dict)})) or "—"
    t.add_row("🚨  breaches (published)", str(len(open_alerts)), "DB:alerts (open)", syms)

    # 6) Dispatch armed (gate summary based on published alerts)
    snoozed = _snoozed(dl)
    armed = bool(live) and n_liq["voice"] and (not snoozed) and (len(open_alerts) > 0)
    gates = " • ".join([
        f"Live {'✓' if live else '✗'}",
        f"Voice {'✓' if n_liq['voice'] else '✗'}",
        f"Snoozed {'✓' if not snoozed else '✗'}",
        f"Breach {'✓' if len(open_alerts) > 0 else '✗'}",
    ])
    t.add_row("🚦  dispatch.armed", "—", "—", f"[bold green]{gates}[/]" if armed else gates)

    # 7) Last attempt (in-memory telemetry; DB attempts also persisted)
    try:
        from backend.services.xcom_status_service import get_last_attempt
        last = get_last_attempt(dl) or {}
    except Exception:
        last = {}
    if last:
        status = last.get("status") or "—"
        who = f"{last.get('provider','twilio')}/{last.get('channel','voice')} → {last.get('to_number','—')}"
        sid = last.get("sid") or "—"
        t.add_row("🕘  last attempt", status, "—", f"{last.get('ts','—')} • {who} • sid={sid}")
    else:
        t.add_row("🕘  last attempt", "—", "—", "no attempts recorded")

    console.print(t)
