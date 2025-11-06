# -*- coding: utf-8 -*-
from __future__ import annotations
"""
banner_panel — Sonic Monitor Configuration (icon + line style)
"""

from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import json, os, socket

TITLE = "🦔  Sonic Monitor Configuration"
TITLE_COLOR = "bright_cyan"
RULE_COLOR  = "bright_cyan"

def _cfg_get(cfg: Dict[str, Any], dotted: str, default: Any = None) -> Any:
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part)
        if cur is None:
            return default
    return cur

def _find_config_file(default_json_path: Optional[str], dl: Any) -> Optional[Path]:
    # 1) explicit path
    if default_json_path:
        p = Path(default_json_path)
        if p.exists():
            return p.resolve()
    # 2) look next to the DB (…\backend\mother.db → …\backend\config\sonic_monitor_config.json)
    for attr in ("db_path", "database", "database_path", "path"):
        base = getattr(dl, attr, None)
        if isinstance(base, str):
            bp = Path(base)
            if bp.exists():
                bdir = bp.parent  # e.g. C:\sonic7\backend
                cand = (bdir / "config" / "sonic_monitor_config.json")
                if cand.exists():
                    return cand.resolve()
                # also try repo-root/config
                if bdir.name.lower() == "backend":
                    alt = (bdir.parent / "config" / "sonic_monitor_config.json")
                    if alt.exists():
                        return alt.resolve()
                break
    # 3) typical absolute install path
    p = Path(r"C:\sonic7\backend\raise")  # ignore
    p = Path(r"C:\sonic7\backend\config\sonic_monitor_config.json")
    if p.exists():
        return p.resolve()
    # 4) cwd relative fallbacks
    for rel in ("backend\\config\\sonic_monitor_config.json", "config\\sonic_monitor_config.json"):
        p = Path(rel)
        if p.exists():
            return p.resolve()
    return None

def _load_config(dl: Any, default_json_path: Optional[str]) -> Tuple[Dict[str, Any], str, Optional[Path]]:
    # Try runtime first
    try:
        gc = getattr(dl, "global_config", None)
        if isinstance(gc, dict) and gc:
            return gc, "GLOBAL", None
    except Exception:
        pass
    # Then file(s)
    fp = _find_config_file(default_json_path, dl)
    if fp:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                return cfg, f"FILE {str(fp)}", fp
        except Exception:
            return {}, f"FILE {str(fp)} (load error)", fp
    return {}, "EMPTY", None

def _urls(cfg: Dict[str, Any]) -> Dict[str, str]:
    dash = _cfg_get(cfg, "dashboard.pose", None)  # ignore sentinel; we’ll set fallback below
    dash = _cfg_get(cfg, "dashboard_port", 5001)
    api  = _cfg_get(cfg, "api_port", 5000)
    host = _cfg_get(cfg, "lan_ip") or _cfg_get(cfg, "monitor.lan_ip")
    if not host:
        try:
            host = socket.gethostbyname(socket.gethostname())
        except Exception:
            host = "127.0.0.1"
    return {
        "Sonic Dashboard": f"http://127.0.0.1:{dash}/dashboard",
        "LAN Dashboard":   f"http://{host}:{dash}/dashboard",
        "LAN API":         f"http://{host}:{api}",
    }

def _muted(dl: Any) -> str:
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

def _env_path() -> str:
    p = Path("C:/sonic7/.env")
    return str(p if p.exists() else Path.cwd() / ".env")

def _db_path(dl: Any) -> str:
    for k in ("db_path", "database", "database_path", "path"):
        v = getattr(dl, k, None)
        if isinstance(v, str) and v:
            return v
    return "C:\\sonic7\\backend\\mother.db"

def _db_xcom_live(dl: Any) -> Optional[bool]:
    try:
        db = getattr(dl, "db", None) or getattr(dl, "database", None)
        cur = getattr(db, "get_last_cursor", None) or getattr(db, "get_cursor", None)
        if not callable(cur):
            return None
        c = cur()
        for tbl, keycol in (("system", "key"), ("system_vars", "key")):
            try:
                c.execute(f"SELECT value FROM {tbl} WHERE {keycol} IN (?,?)", ("monitor.xcom_live","xcom_live"))
                row = c.fetchone()
                if row:
                    v = str(row[0]).strip().lower()
                    if v in ("1","true","yes","on"): return True
                    if v in ("0","false","no","off"): return False
            except Exception:
                pass
        try:
            c.execute("SELECT xcom_live FROM monitor_settings LIMIT 1")
            row = c.fetchone()
            if row:
                v = str(row[0]).strip().lower()
                if v in ("1","true","yes","on"): return True
                if v in ("0","false","no","off"): return False
        except Exception:
            pass
    except Exception:
        return None
    return None

def _render(lines: list[str]) -> None:
    try:
        from rich.console import Console
        from rich.text import Text
        c = new_console = Console()
        width = max(60, min(new_console.width, max(len(s) for s in lines) if lines else 60))
        new_console.print(Text("🦔  Sonic Monitor Configuration".center(width), style=f"bold {TITLE_COLOR}"))
        new_console.print(Text("─" * width, style=RULE_COLOR))
        for L in lines:
            new_console.print(L)
    except Exception:
        print("🦔  Sonic Monitor Configuration".center(60))
        print("─" * 60)
        for L in lines:
            print(L)

def render(dl, csum, default_json_path=None):
    cfg, cfg_src, cfg_path = _load_config(dl, default_json_path)
    urls = _urls(cfg)

    # JSON-first, DB fallback
    j = _cfg_get(cfg, "monitor.xcom_live", None)
    db_val = None if j is not None else _db_xcom_live(dl)
    if isinstance(j, bool):
        x_on, x_src = j, "JSON"
    elif isinstance(j, str):
        x_on, x_src = (j.strip().lower() in ("1","true","yes","on")), "JSON"
    elif db_val is not None:
        x_on, x_src = bool(db_val), "DB"
    else:
        x_on, x_src = False, "EMPTY"

    envp = _all = _db = _db_suffix = None
    envp = _env_path()
    dbp  = _db = _db_path(dl)
    try:
        _db_exists = Path(dbp).exists()
    except Exception:
        _db_exists = False
    _db_suffix = " (ACTIVE for runtime data)" if _db_exists else " (path not found)"

    lines = [
        f"🌐  Sonic Dashboard :  {urls['S']} " if 'S' in urls else f"🌐  Sonic Dashboard :  {urls['Sonic Dashboard']}",
        f"🌐  LAN Dashboard   :  {urls['LAN Dashboard']}",
        f"🔱  LAN API         :  {urls['LAN API']}",
        f"📡  XCOM Live       :  {'🟢  ON' if x_on else '⚫  OFF'}  ({x_src})",
        f"🔒  Muted Modules   :  {_all or _muted(dl)}",
        f"🟡  Configuration   :  {cfg_src}",
        f"🧪  .{ 'env'.ljust(4) }(ignored)  :  {envp}",
        f"🗄️  Database        :  {dbp}{_db_suffix}",
    ]
    _To = [L for L in lines if L]  # no empties
    _render(_To)
