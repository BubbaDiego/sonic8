# -*- coding: utf-8 -*-
from __future__ import annotations
"""
banner_panel — Sonic Monitor Configuration (icon + line style)

Contract (sequencer):
  render(dl, csum, default_json_path=None)
"""

from typing import Any, Dict, Optional
from pathlib import Path
import json
import os


# ---------- small helpers ----------

def _safe(obj: Any, *attrs: str, default=None):
    for a in attrs:
        try:
            v = getattr(obj, a)
        except Exception:
            v = None
        if v not in (None, ""):
            return v
    return default

def _trueish(x: Any) -> bool:
    if isinstance(x, str):
        return x.strip().lower() in {"1", "true", "on", "yes", "y"}
    return bool(x)

def _read_json(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _guess_env_path() -> str:
    p = Path("C:/sonic7/.env")
    return str(p if p.exists() else Path.cwd() / ".env")

def _guess_lan_ip(cfg: Dict[str, Any]) -> str:
    ip = (
        cfg.get("lan_ip")
        or cfg.get("host_ip")
        or os.environ.get("SONIC_LAN_IP")
    )
    if ip:
        return str(ip)
    try:
        import socket
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "192.168.0.100"

def _db_path_from_dl(dl) -> str:
    return _safe(dl, "db_path", "database", "database_path",
                 default="C:\\sonic7\\backend\\mother.db")

def _muted_from_dl(dl) -> str:
    vals = _safe(dl, "muted_modules", "muted", default=None)
    if vals is None:
        return "—"
    if isinstance(vals, str):
        parts = [v.strip() for v in vals.split(",") if v.strip()]
    else:
        try:
            parts = [str(v) for v in vals]
        except Exception:
            parts = []
    return ", ".join(parts) if parts else "—"


# ---------- rendering ----------

TITLE = "🌀 🌀 🌀  Sonic Monitor  🌀 🌀 🌀"
TITLE_COLOR = "bright_cyan"
RULE_COLOR  = "bright_cyan"

def _render_rich(lines: list[str]) -> None:
    try:
        from rich.console import Console
        from rich.text import Text
    except Exception:
        _render_plain(lines)
        return

    console = Console()
    width = max(60, min(console.width, max(len(l) for l in lines) if lines else 60))

    # Title + single cyan rule (no table headers)
    console.print(Text(TITLE.center(width), style=f"bold {TITLE_COLOR}"))
    console.print(Text("─" * width, style=RULE_COLOR))

    # Body lines with icons (exactly one line per item)
    for l in lines:
        console.print(l)

def _render_plain(lines: list[str]) -> None:
    width = max(60, max(len(l) for l in lines) if lines else 60)
    print(TITLE.center(width))
    print("─" * width)
    for l in lines:
        print(l)


# ---------- panel entry ----------

def render(dl, csum, default_json_path=None):
    cfg_path = str(default_json_path) if default_json_path else None
    cfg = _read_json(cfg_path)

    dash_port = cfg.get("dashboard_port") or 5001
    api_port  = cfg.get("api_port") or 5000
    lan_ip    = _guess_lan_ip(cfg)

    sonic_dash = f"http://127.0.0.1:{dash_port}/dashboard"
    lan_dash   = f"http://{lan_ip}:{dash_port}/dashboard"
    lan_api    = f"http://{lan_ip}:{api_port}"

    # XCOM
    xcom_live = _trueish(
        _safe(dl, "xcom_live", "xcom_enabled", default=None)
        or os.environ.get("XCOM_LIVE")
        or cfg.get("xcom_live", False)
    )
    xcom_status = "🟢  ON [FILE]" if xcom_live else "⚫  OFF"

    # Muted, config, env, database
    muted = _muted_from_dl(dl)
    env_path = _guess_env_path()
    cfg_display = f"JSON ONLY  –  {cfg_path}" if cfg_path else "—"

    db_path = _db_path_from_dl(dl)
    if Path(db_path).exists():
        db_suffix = " (ACTIVE for runtime data, provenance=DEFAULT, exists, inside repo)"
    else:
        db_suffix = " (path not found)"

    # Build the icon+line body (no table headers)
    lines = [
        f"🌐  Sonic Dashboard :  {sonic_dash}",
        f"🌐  LAN Dashboard   :  {lan_dash}",
        f"🔱  LAN API         :  {lan_api}",
        f"📡  XCOM Live       :  {xcom_status}",
        f"🔒  Muted Modules   :  {muted}",
        f"🟡  Configuration   :  {cfg_display}",
        f"🧪  .env (ignored)  :  {env_path}",
        f"🗄️  Database        :  {db_path}{db_suffix}",
    ]

    _render_rich(lines)
