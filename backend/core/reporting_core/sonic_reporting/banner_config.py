# -*- coding: utf-8 -*-
from __future__ import annotations
import socket
from pathlib import Path
from .writer import write_line
from .styles import ICON_CFG, ICON_DASH, ICON_API, ICON_LOCKS, ICON_TOGGLE

def _lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip.startswith("127."): raise RuntimeError()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

def render_banner(dl, json_path: str) -> None:
    print("══════════════════════════════════════════════════════════════")
    write_line(f"{ICON_CFG} Sonic Monitor Configuration")
    print("══════════════════════════════════════════════════════════════")
    lan = _lan_ip()
    write_line(f"{ICON_DASH} Sonic Dashboard: http://127.0.0.1:5001/dashboard")
    write_line(f"{ICON_DASH} LAN Dashboard : http://{lan}:5001/dashboard")
    write_line(f"{ICON_API} LAN API      : http://{lan}:5000")
    # XCOM toggle
    try:
        xcom_active = (dl.global_config.get("xcom") or {}).get("active", False)  # type: ignore
        xcom_src    = "FILE"
    except Exception:
        xcom_active, xcom_src = False, "—"
    write_line(f"{ICON_TOGGLE} XCOM Active  : {'ON' if xcom_active else 'OFF'}   [{xcom_src}]")

    # Muted modules list (matches existing suppression set)
    write_line(f"{ICON_LOCKS} Muted Modules:      ConsoleLogger, console_logger, LoggerControl, werkzeug, uvicorn.access, fuzzy_wuzzy, asyncio")

    # Configuration mode and paths
    write_line(f"🧭 Configuration: JSON ONLY — {json_path}")
    # best-effort upward search for .env starting from backend/
    try:
        backend_dir = Path(__file__).resolve().parents[4]
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

    # Database path information
    db_path = None
    for attr in ("db_path", "path", "database_path", "filename"):
        try:
            val = getattr(getattr(dl, "db", None), attr, None)
            if val:
                db_path = str(val)
                break
        except Exception:
            pass
    if not db_path:
        db_path = "mother.db"
    try:
        db_exists = Path(db_path).exists()
        repo_root = Path(__file__).resolve().parents[4]
        inside_repo = str(Path(db_path)).startswith(str(repo_root))
    except Exception:
        db_exists = True
        inside_repo = True
    write_line(
        f"🔌 Database       : {db_path}  (ACTIVE for runtime data, provenance=DEFAULT, {'exists' if db_exists else 'missing'}, {'inside repo' if inside_repo else 'outside repo'})"
    )
