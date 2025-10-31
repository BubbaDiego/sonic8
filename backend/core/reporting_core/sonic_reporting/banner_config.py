# -*- coding: utf-8 -*-
from __future__ import annotations
import socket
import os
from pathlib import Path
from .writer import write_line

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

def _as_bool(val) -> tuple[bool, bool]:
    """
    Return (is_bool, value). Accepts real bool or common string/int truthy values.
    """
    if isinstance(val, bool):
        return True, val
    if isinstance(val, (int, float)):
        return True, bool(val)
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("1", "true", "on", "yes", "y"):
            return True, True
        if v in ("0", "false", "off", "no", "n"):
            return True, False
    return False, False

def _xcom_live_status(dl) -> tuple[bool, str]:
    """
    Report whether XCOM is live (ON/OFF) and the source: RUNTIME | FILE | DB | ENV | —.
    Preference order: RUNTIME → FILE → DB → ENV.
    """
    # 1) RUNTIME: check common service hooks on DataLocker
    try:
        for name in ("voice_service", "xcom_voice", "xcom", "voice"):
            svc = getattr(dl, name, None)
            if svc is None:
                continue
            # properties on the object
            for flag in ("is_live", "live", "enabled", "is_enabled", "active"):
                try:
                    val = getattr(svc, flag, None)
                except Exception:
                    val = None
                ok, b = _as_bool(val)
                if ok:
                    return b, "RUNTIME"
            # dict-like
            if isinstance(svc, dict):
                for flag in ("enabled", "is_enabled", "active", "live", "is_live"):
                    if flag in svc:
                        ok, b = _as_bool(svc.get(flag))
                        if ok:
                            return b, "RUNTIME"
    except Exception:
        pass

    # 2) FILE: global_config
    try:
        gc = getattr(dl, "global_config", None) or {}
        channels = gc.get("channels") or {}
        voice = channels.get("voice") or gc.get("xcom") or {}
        ok, b = _as_bool(voice.get("enabled"))
        if ok:
            return b, "FILE"
        ok, b = _as_bool(voice.get("active"))
        if ok:
            return b, "FILE"
    except Exception:
        pass

    # 3) DB: system vars
    try:
        sysvars = getattr(dl, "system", None)
        if sysvars:
            x = (sysvars.get_var("xcom") or {})
            ok, b = _as_bool(x.get("active"))
            if ok:
                return b, "DB"
            ok, b = _as_bool(x.get("enabled"))
            if ok:
                return b, "DB"
            ok, b = _as_bool(x.get("live"))
            if ok:
                return b, "DB"
    except Exception:
        pass

    # 4) ENV
    env = os.getenv("XCOM_LIVE", os.getenv("XCOM_ACTIVE", ""))
    ok, b = _as_bool(env)
    if ok:
        return b, "ENV"

    return False, "—"

def render_banner(dl, json_path: str) -> None:
    # Framed header
    print("══════════════════════════════════════════════════════════════")
    write_line("🦔 Sonic Monitor Configuration")
    print("══════════════════════════════════════════════════════════════")

    lan = _lan_ip()
    write_line(f"🌐 Sonic Dashboard: http://127.0.0.1:5001/dashboard")
    write_line(f"🌐 LAN Dashboard : http://{lan}:5001/dashboard")
    write_line(f"🔌 LAN API      : http://{lan}:5000")

    # XCOM Live (runtime-first)
    from .xcom_extras import xcom_live_status
    cfg_for_probe = getattr(dl, "global_config", None)
    live, src = xcom_live_status(dl, cfg_for_probe)
    status = "🟢 ON" if live else "🔴 OFF"
    write_line(f"🛰 XCOM Live : {status} [{src}]")

    # Muted modules
    write_line("🔒 Muted Modules:      ConsoleLogger, console_logger, LoggerControl, "
               "werkzeug, uvicorn.access, fuzzy_wuzzy, asyncio")

    # Configuration path
    write_line(f"🧭 Configuration: JSON ONLY — {json_path}")

    # .env path (search up from backend/)
    try:
        backend_dir = Path(__file__).resolve().parents[4]   # …/backend
        candidates = [backend_dir / ".env",
                      backend_dir.parent / ".env",
                      backend_dir.parent.parent / ".env"]
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
                db_path = str(val); break
    except Exception:
        pass
    db_path = db_path or "mother.db"
    try:
        backend_dir = Path(__file__).resolve().parents[4]
        exists = Path(db_path).exists()
        inside_repo = str(db_path).startswith(str(backend_dir))
    except Exception:
        exists, inside_repo = True, True
    write_line(f"🔌 Database       : {db_path}  (ACTIVE for runtime data, provenance=DEFAULT, "
               f"{'exists' if exists else 'missing'}, {'inside repo' if inside_repo else 'outside repo'})")
