# -*- coding: utf-8 -*-
from __future__ import annotations
"""
banner_panel — Sonic Monitor Configuration (icon + line style)

Contract (sequencer):
  render(dl, csum, default_json_path=None)

- Discover config in this order: dl.global_config → explicit default_json_path →
  <repo>/backend/config/sonic_monitor_config.json → ./backend/config/… → ./config/…
- Resolve XCOM live from JSON (monitor.xcom_live) first, then DB fallback.
- Display provenance in parentheses: (JSON) or (DB); (EMPTY) if neither found.
- Show configuration source (GLOBAL/FILE <path>/EMPTY), LAN/API URLs, muted modules, env and DB paths.
"""

from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import json
import socket

TITLE = "🦔  Sonic Monitor Configuration"
TITLE_COLOR = "bright_cyan"
RULE_COLOR  = "bright_cyan"

# ───────────── helpers: config & system info ─────────────

def _cfg_get(cfg: Dict[str, Any], dotted: str, default: Any = None) -> Any:
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part)
        if cur is None:
            return default
    return cur

def _db_path_from_dl(dl: Any) -> Optional[Path]:
    for attr in ("db_path", "database", "database_path", "path"):
        v = getattr(dl, attr, None)
        if isinstance(v, str) and v:
            return Path(v)
    return None

def _discover_config_path(dl: Any, default_json_path: Optional[str]) -> Optional[Path]:
    # 1) explicit param
    if default_json_path:
        p = Path(default_json_path)
        if p.exists():
            return p.resolve()
    # 2) derive from the running DB location (…\backend\mother.db → …\backend\config\sonic_monitor_config.json)
    bp = _db_path_from_dl(dl)
    if bp and bp.exists():
        b = bp.parent  # …\backend
        cand = (b / "config" / "sonic_monitor_config.json")
        if cand.exists():
            return cand.resolve()
        # also try repo-root\config\sonic_monitor_config.json if we’re under <repo>\backend\…
        if b.name.lower() == "backend":
            alt = (b.parent / "config" / "sonic_monitor_config.json")
            if alt.exists():
                return alt.resolve()
    # 3) typical absolute install path (your machine layout)
    p = Path(r"C:\sonic7\backend\config\").joinpath("sonic_mate", "sonic_monitor_config.json")
    if p.exists():
        return p.resolve()
    p = Path(r"C:\sonic7\backend\config\sonic_monitor_config.json")
    if p.exists():
        return p.resolve()
    # 4) cwd fallbacks
    for rel in ("backend\\config\\sonic_monitor_config.json", "config\\sonic_monitor_config.json"):
        p = Path(rel)
        if p.exists():
            return p.resolve()
    return None

def _load_config(dl: Any, default_json_path: Optional[str]) -> Tuple[Dict[str, Any], str, Optional[Path]]:
    """Return (cfg, source_label, file_path)."""
    # Prefer runtime/global injection
    try:
        gc = getattr(dl, "global_config", None)
        if isinstance(gc, dict) and gc:
            return gc, "GLOBAL", None
    except Exception:
        pass

    fp = _discover_config_path(dl, default_json_path)
    if fp:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                return cfg, f"FILE {str(fp)}", fp
        except Exception:
            return {}, f"FILE {str(fp)} (load error)", fp

    return {}, "EMPTY", None

def _resolve_xcom_live(cfg: Dict[str, Any], dl: Any) -> Tuple[bool, str, str]:
    """
    Returns (is_on, source_label, detail_source_label)
      is_on: bool
      source_label: 'JSON' | 'DB' | 'EMPTY'  (for printing in parentheses)
      detail: human-readable where it came from: 'JSON', 'DB', or 'EMPTY'
    Uses JSON first (cfg['monitor']['xcom_live']), then DB fallback on dl.db.
    """
    raw = _cfg_get(cfg, "monitor.xcom_live", None)
    if raw is not None:
        val = raw if isinstance(raw, bool) else (str(raw).strip().lower() in ("1","true","yes","on"))
        return bool(val), "JSON", "JSON"

    # DB fallback, first check system tables, then monitor_settings
    try:
        db = getattr(dl, "db", None) or getattr(dl, "database", None)
        getcur = getattr(db, "get_cursor", None)
        if callable(getcur):
            cur = getcur()
            # system / system_vars
            for tbl, keycol in (("system", "key"), ("system_vars", "key")):
                try:
                    cur.execute(f"SELECT value FROM {tbl} WHERE {keycol} IN (?,?)", ("monitor.xcom_live","xcom_live"))
                    row = cur.fetchone()
                    if row:
                        v = str(row[0]).strip().lower()
                        if v in ("1","true","yes","on"):
                            return True, "DB", "DB"
                        if v in ("0","false","no","off"):
                            return False, "DB", "DB"
                except Exception:
                    pass
            # monitor_settings.xcom_* (if present)
            try:
                cur.execute("SELECT xcom_live FROM monitor_settings LIMIT 1")
                row = cur.fetchone()
                if row is not None:
                    v = str(row[0]).strip().lower()
                    if v in ("1","true","yes","on"):
                        return True, "DB", "DB"
                    if v in ("0","false","no","off"):
                        return False, "DB", "DB"
            except Exception:
                pass
    except Exception:
        pass

    return False, "EMPTY", "EMPTY"

def _urls(cfg: Dict[str, Any]) -> Dict[str, str]:
    dash = _cfg_get(cfg, "dashboard_port", 5001)
    api  = _cfg_get(cfg, "api_port", 5000)
    host = _cfg_get(cfg, "lan_ip") or _cfg_get(cfg, "monitor.lan_ip")
    if not host:
        try:
            host = socket.gethostbyname(socket.gethostname())
        except Exception:
            host = "127.0.0.1"
    return {
        "Sonic": f"http://127.0.0.1:{dash}/dashboard",
        "LAN_DASH": f"http://{host}:{dash}/dashboard",
        "LAN_API":  f"http://{host}:{api}",
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

def _env_path() -> str:
    p = Path("C:/sonic7/.env")
    return str(p if p.exists() else Path.cwd() / ".env")

# ─────────────────── rendering ───────────────────

def _render(lines: list[str]) -> None:
    try:
        from rich.console import Console
        from rich.text import Text
        c = Console()
        width = max(60, min(c.width, max(len(s) for s in lines) if lines else 60))
        c.print(Text(TITLE.center(width), style=f"bold {TITLE_COLOR}"))
        c.print(Text("─" * width, style=RULE_COLOR))
        for line in lines:
            c.print(line)
    except Exception:
        print(TITLE.center(60))
        print("─" * 60)
        for line in lines:
            print(line)

# ─────────────────── entry ───────────────────

def render(dl, csum, default_json_path=None):
    cfg, cfg_src, _ = _load_config(dl, default_json_path)
    urls = _urls(cfg)

    x_on, x_src, _detail_src = _resolve_xcom_live(cfg, dl)

    dbp = _db_path_from_dl(dl)
    db_suffix = ""
    try:
        if dbp and dbp.exists():
            db_suffix = " (ACTIVE for runtime data)"
        elif dbp is not None:
            db_suffix = " (path not found)"
    except Exception:
        db_suffix = ""

    thresholds = getattr(dl, "get_liquid_thresholds", lambda: {})()

    def _fmt_thr(val: Any) -> str:
        try:
            if val is None:
                return "—"
            num = float(val)
            if num.is_integer():
                return f"{int(num)}"
            return f"{num:g}"
        except Exception:
            return "—"

    lines = [
        f"🌐  Sonic Dashboard :  {urls['Sonic']}",
        f"🌐  LAN Dashboard   :  {urls['LAN_DASH']}",
        f"🔱  LAN API         :  {urls['LAN_API']}",
        f"📡  XCOM Live       :  {'🟢  ON' if x_on else '⚫  OFF'}  ({x_src})",
        f"🔒  Muted Modules   :  {_muted_modules(dl)}",
        f"🟡  Configuration   :  {cfg_src}",
        "💧  Liquid thresholds :  "
        + f"🟡 BTC {_fmt_thr(thresholds.get('BTC'))}"
        + " • "
        + f"🔷 ETH {_fmt_thr(thresholds.get('ETH'))}"
        + " • "
        + f"🟣 SOL {_fmt_thr(thresholds.get('SOL'))}",
        f"🧪  .env (ignored)  :  {_env_path()}",
        f"🗄️  Database        :  {str(dbp) if dbp else '—'}{db_suffix}",
    ]
    _render([ln for ln in lines if ln])
