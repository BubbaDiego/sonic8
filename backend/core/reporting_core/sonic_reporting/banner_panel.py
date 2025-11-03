# -*- coding: utf-8 -*-
from __future__ import annotations

import socket
from pathlib import Path

from .config_probe import discover_json_path, parse_json
from .writer import write_line
from .xcom_extras import xcom_live_status


def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip.startswith("127."):
            raise RuntimeError("loopback")
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def render_banner(dl, default_json_path: str) -> None:
    # Framed header
    print("══════════════════════════════════════════════════════════════")
    write_line("🦔 Sonic Monitor Configuration")
    print("══════════════════════════════════════════════════════════════")

    lan = _lan_ip()
    write_line("🌐 Sonic Dashboard: http://127.0.0.1:5001/dashboard")
    write_line(f"🌐 LAN Dashboard : http://{lan}:5001/dashboard")
    write_line(f"🔌 LAN API      : http://{lan}:5000")

    # XCOM Live (unified JSON-aware probe: FILE > DB > ENV)
    try:
        _path = discover_json_path(default_json_path)
        _cfg_obj, _err, _meta = parse_json(_path)
        _cfg_for_probe = _cfg_obj if isinstance(_cfg_obj, dict) else getattr(dl, "global_config", None)
    except Exception:
        _cfg_for_probe = getattr(dl, "global_config", None)

    _live, _src = xcom_live_status(dl, _cfg_for_probe)
    print(f"  🛰 XCOM Live : {'🟢 ON' if _live else '🔴 OFF'} [{_src}]")

    # Muted modules
    write_line(
        "🔒 Muted Modules:      ConsoleLogger, console_logger, LoggerControl, "
        "werkzeug, uvicorn.access, fuzzy_wuzzy, asyncio"
    )

    # Configuration path
    try:
        json_path = discover_json_path(default_json_path)
    except Exception:
        json_path = default_json_path
    write_line(f"🧭 Configuration: JSON ONLY — {json_path}")

    # .env path (search up from backend/)
    try:
        backend_dir = Path(__file__).resolve().parents[4]   # …/backend
        candidates = [
            backend_dir / ".env",
            backend_dir.parent / ".env",
            backend_dir.parent.parent / ".env",
        ]
        found = next((c for c in candidates if c.exists()), None)
        env_path = str(found or (backend_dir / ".env"))
    except Exception:
        env_path = ".env"
    write_line(f"📦 .env (ignored for config) : {env_path}")

    # Database path & hints
    db_path = None
    try:
        db = getattr(dl, "db", None)
        for attr in ("db_path", "path", "database_path", "filename"):
            val = getattr(db, attr, None)
            if val:
                db_path = str(val)
                break
    except Exception:
        pass
    db_path = db_path or "mother.db"
    try:
        backend_dir = Path(__file__).resolve().parents[4]
        exists = Path(db_path).exists()
        inside_repo = str(db_path).startswith(str(backend_dir))
    except Exception:
        exists, inside_repo = True, True
    write_line(
        f"🔌 Database       : {db_path}  (ACTIVE for runtime data, provenance=DEFAULT, "
        f"{'exists' if exists else 'missing'}, {'inside repo' if inside_repo else 'outside repo'})"
    )


def render(dl, default_json_path: str | None = None) -> None:
    try:
        render_banner(dl, default_json_path or "")
    except NameError:
        # fallback: inline import if render_banner was renamed/removed
        try:
            from .banner_panel import render_banner as _render_banner

            _render_banner(dl, default_json_path or "")
        except Exception:
            pass
