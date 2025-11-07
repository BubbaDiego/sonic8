# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Optional, Dict

from rich.console import Console
from rich.table import Table
from rich.text import Text

# Alerts DB
from backend.data import dl_alerts

# Config resolution: use the same helper other panels use
try:
    from backend.core.reporting_core.sonic_reporting.config_probe import discover_json_path, parse_json
except Exception:
    def discover_json_path(_): return None
    def parse_json(_): return {}, None, {}

# Live resolver (same as banner/sync)
try:
    from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_live_status
except Exception:
    def xcom_live_status(dl: Any, cfg: dict | None = None) -> tuple[bool, str]:
        v = getattr(dl, "xcom_live", None)
        return (bool(v), "RUNTIME") if isinstance(v, bool) else (False, "—")

# Dispatcher telemetry (still shown in panel)
try:
    from backend.services.xcom_status_service import get_last_attempt
except Exception:
    def get_last_attempt(_): return None


def _chip_on_off(v: bool) -> Text:
    return Text("🟢  ON", style="bold green") if v else Text("🔴  OFF", style="bold red")

def _load_cfg() -> tuple[dict, Optional[str]]:
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


def _extract_notifications(cfg: Dict) -> Dict[str, bool]:
    n = cfg.get("liquid", {}).get("notifications", {}) or {}
    return {
        "voice": bool(n.get("voice", True)),
        "system": bool(n.get("system", True)),
        "tts": bool(n.get("tts", True)),
        "sms": bool(n.get("sms", False)),
    }


def render(dl: Any, csum: Optional[dict] = None) -> None:
    console = Console()
    t = Table(title="🧪  XCOM Check", show_header=True, header_style="bold")
    t.add_column("Check")
    t.add_column("Status", justify="center")
    t.add_column("Details")

    cfg, cfg_path = _load_cfg()
    t.add_row("cfg source", Text("✅" if cfg_path else "—"), Text(f"FILE {cfg_path}" if cfg_path else "[-]"))

    live, live_src = xcom_live_status(dl, cfg=cfg or getattr(dl, "global_config", None))
    t.add_row("📡  XCOM Live", _chip_on_off(bool(live)), Text(f"[{live_src}]"))

    notif = _extract_notifications(cfg)
    chips = "  ".join([
        "📞 " + ("✅" if notif["voice"] else "❌"),
        "🖥️ " + ("✅" if notif["system"] else "❌"),
        "🔊 " + ("✅" if notif["tts"] else "❌"),
        "💬 " + ("✅" if notif["sms"] else "❌"),
    ])
    t.add_row("channels(liquid)", Text("✅"), Text(chips))

    # Published alerts (canonical source) — only 'open' breach alerts for liquid monitor
    open_alerts = dl_alerts.list_open(dl, kind="breach", monitor="liquid")
    pub_ok = len(open_alerts) > 0
    sym_list = ", ".join(sorted({a["symbol"] for a in open_alerts})) if pub_ok else "—"
    t.add_row("breaches (published)", Text("✅" if pub_ok else "—"), Text(f"{len(open_alerts)} • {sym_list}"))

    # Armed summary: uses published alerts (single path), not transient flags
    snoozed = False
    for key in ("monitor_snoozed", "liquid_snoozed", "liquid_snooze"):
        v = getattr(dl, key, 0)
        try:
            if float(v) > 0: snoozed = True
        except Exception:
            if isinstance(v, bool) and v: snoozed = True

    armed = bool(live) and notif["voice"] and (not snoozed) and pub_ok
    why = " • ".join([
        f"Live {'✓' if live else '✗'}",
        f"Voice {'✓' if notif['voice'] else '✗'}",
        f"Snoozed {'✓' if not snoozed else '✗'}",
        f"Breach {'✓' if pub_ok else '✗'}",
    ])
    t.add_row("dispatch.armed", Text("✅" if armed else "❌"), Text(why))

    # Last attempt (still helpful)
    last = get_last_attempt(dl) or {}
    if last:
        status = last.get("status")
        label = {"success":"🟢 success","fail":"🔴 fail","skipped":"⚪ skipped"}.get(status, status or "—")
        who = f"{last.get('provider','twilio')}/{last.get('channel','voice')} → {last.get('to_number','—')}"
        sid = last.get("sid") or "—"
        src = last.get("source", "monitor")
        t.add_row("last attempt", Text(label), Text(f"{last.get('ts','—')} • {who} • sid={sid} [{src}]"))
    else:
        t.add_row("last attempt", Text("—"), Text("no attempts recorded"))

    console.print(t)
