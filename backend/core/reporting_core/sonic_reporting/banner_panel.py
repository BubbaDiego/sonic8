# -*- coding: utf-8 -*-
from __future__ import annotations
"""
banner_panel — Sonic Monitor Configuration (icon + line style)

Contract (sequencer):
  render(dl, csum, default_json_path=None)

Requirements:
- Resolve XCOM Live from JSON first, then DB. Show source as (JSON) or (DB).
- Config discovery must actually find C:\sonic7\backend\config\sonic_monitor_config.json
  even if cwd is different.
- Preserve single-line icon-first layout.
"""

from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import json
import os
import socket


# ─────────────────── helpers: paths & IO ───────────────────

def _db_path_from_dl(dl: Any) -> str:
    for k in ("db_path", "database", "database_path", "path"):
        v = getattr(dl, k, None)
        if isinstance(v, str) and v:
            return v
    return "C:\\sonic7\\backend\\mother.db"

def _repo_root_guess(dl: Any) -> Optional[Path]:
    """
    Try to derive repo root from DB path like C:\sonic7\backend\mother.db → C:\sonic7
    """
    try:
        dbp = Path(_db_path_from_dl(dl))
        # .../backend/mother.db -> repo root is parent of 'backend'
        if dbp.exists():
            # dbp = .../backend/mother.db  -> dbp.parent.name == 'backend'
            if dbp.parent.name.lower() == "backend":
                return dbp.parent.parent
            # If not the expected shape, try two levels up anyway
            return dbp.parent.parent
    except Exception:
        pass
    return None

def _discover_json_path(dl: Any, default_json_path: Optional[str]) -> Optional[str]:
    """
    Prefer explicit default_json_path. Then try absolute & repo-derived candidates.
    """
    # 0) Explicit
    if default_json_path:
        p = Path(default_json_path)
        if p.exists():
            return str(p)

    # 1) Absolute typical install path
    absolute_candidate = Path(r"C:\sonic7\backend\config\sonic_monitor_config.json")
    if absolute_candidate.exists():
        return str(absolute_candidate)

    # 2) Repo-root based candidates (in case cwd differs)
    root = _repo_root_guess(dl)
    if root:
        for rel in ("backend/config/sonic_monitor_config.json",
                    "config/sonic_monitor_config.json"):
            p = root / rel
            if p.exists():
                return str(p)

    # 3) CWD-based (as last resort)
    for rel in ("backend/config/sonic_monitor_config.json",
                "config/sonic_monitor_config.json"):
        p = Path(rel)
        if p.exists():
            return str(p)

    return None

def _load_json_config(dl: Any, default_json_path: Optional[str]) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Return (cfg, file_path) or ({}, None) if not found/loaded.
    """
    path = _discover_json_path(dl, default_json_path)
    if not path:
        return {}, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return (cfg if isinstance(cfg, dict) else {}), path
    except Exception:
        return {}, None

def _cfg_get(cfg: Dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = cfg
    try:
        for key in path.split("."):
            cur = cur.get(key) if isinstance(cur, dict) else None
        return default if cur is None else cur
    except Exception:
        return default


# ─────────────────── DB helpers ───────────────────

def _db_bool(x: Any) -> Optional[bool]:
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    if s in {"1", "true", "on", "yes", "y"}:
        return True
    if s in {"0", "false", "off", "no", "n"}:
        return False
    return None

def _db_xcom_live(dl: Any) -> Optional[bool]:
    """
    Best-effort DB read:
      - system_vars(key='monitor.xcom_live' or 'xcom_live')
      - monitor_settings(xcom_live)
    Return True/False/None.
    """
    try:
        db = getattr(dl, "db", None)
        cur = getattr(db, "get_cursor", None)
        if not callable(cur):
            return None
        c = cur()

        # system_vars
        for key in ("monitor.xcom_live", "xcom_live"):
            try:
                c.execute("SELECT value FROM system_vars WHERE key=?", (key,))
                row = c.fetchone()
                if row and len(row) >= 1:
                    val = _db_bool(row[0])
                    if val is not None:
                        return val
            except Exception:
                pass

        # monitor_settings
        try:
            c.execute("SELECT xcom_live FROM monitor_settings LIMIT 1")
            row = c.fetchone()
            if row and len(row) >= 1:
                val = _db_bool(row[0])
                if val is not None:
                    return val
        except Exception:
            pass

    except Exception:
        return None
    return None


# ─────────────────── formatting helpers ───────────────────

def _guess_env_path() -> str:
    p = Path("C:/sonic7/.env")
    return str(p if p.exists() else Path.cwd() / ".env")

def _lan_ip(cfg: Dict[str, Any]) -> str:
    ip = _cfg_get(cfg, "lan_ip") or _cfg_get(cfg, "monitor.lan_ip")
    if isinstance(ip, str) and ip:
        return ip
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "192.168.0.100"

def _urls(cfg: Dict[str, Any]) -> Dict[str, str]:
    dash_port = _cfg_get(cfg, "dashboard_port", 5001)
    api_port  = _cfg_get(cfg, "api_port", 5000)
    ip = _lan_ip(cfg)
    return {
        "Sonic Dashboard": f"http://127.0.0.1:{dash_port}/dashboard",
        "LAN Dashboard":   f"http://{ip}:{dash_port}/dashboard",
        "LAN API":         f"http://{ip}:{api_port}",
    }

def _muted_modules(dl: Any) -> str:
    vals = getattr(dl, "muted_modules", None) or getattr(dl, "muted", None)
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


# ─────────────────── rendering (Rich + fallback) ───────────────────

TITLE = "🦔  Sonic Monitor Configuration"
TITLE_COLOR = "bright_cyan"
RULE_COLOR  = "bright_cyan"

def _render_rich(lines: list[str]) -> None:
    try:
        from rich.console import Console
        from rich.text import Text
    except Exception:
        _render_plain(lines); return

    console = Console()
    width = max(60, min(console.width, max(len(l) for l in lines) if lines else 60))
    console.print(Text(TITLE.center(width), style=f"bold {TITLE_COLOR}"))
    console.print(Text("─" * width, style=RULE_COLOR))
    for l in lines:
        console.print(l)

def _render_plain(lines: list[str]) -> None:
    width = max(60, max(len(l) for l in lines) if lines else 60)
    print(TITLE.center(width))
    print("─" * width)
    for l in lines:
        print(l)


# ─────────────────── panel entry ───────────────────

def render(dl, csum, default_json_path=None):
    # 1) Load JSON (preferred)
    cfg_json, cfg_path = _load_json_config(dl, default_json_path)
    urls = _urls(cfg_json)

    # 2) Resolve XCOM Live — JSON → DB
    x_json = _cfg_get(cfg_json, "monitor.xcom_live", None)
    x_db   = None if x_json is not None else _db_xcom_live(dl)

    if x_json is not None:
        xcom_live = bool(x_json)
        x_src = "JSON"
    elif x_db is not None:
        xcom_live = bool(x_db)
        x_src = "DB"
    else:
        xcom_live = False
        x_src = "EMPTY"

    # 3) Other banner bits
    muted    = _muted_modules(dl)
    env_path = _guess_env_path()
    db_path  = _db_path_from_dl(dl)
    try:
        db_exists = Path(db_path).exists()
    except Exception:
        db_exists = False
    db_suffix = " (ACTIVE for runtime data)" if db_exists else " (path not found)"

    cfg_display = f"FILE {cfg_path}" if cfg_path else "EMPTY"

    # 4) Compose lines (single-line per item)
    lines = [
        f"🌐  Sonic Dashboard :  {urls['Sonic Dashboard']}",
        f"🌐  LAN Dashboard   :  {urls['LAN Dashboard']}",
        f"🔱  LAN API         :  {urls['LAN API']}",
        f"📡  XCOM Live       :  {'🟢  ON' if xcom_live else '⚫  OFF'}   ({x_src})",
        f"🔒  Muted Modules   :  {muted}",
        f"🟡  Configuration   :  {cfg_display}",
        f"🧪  .env (ignored)  :  {env_path}",
        f"🗄️  Database        :  {db_path}{db_suffix}",
    ]

    _render_rich(lines)
