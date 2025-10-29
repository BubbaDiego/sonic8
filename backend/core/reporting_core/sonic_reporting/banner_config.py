# -*- coding: utf-8 -*-
from __future__ import annotations
import socket
from .writer import write_line
from .styles import ICON_CFG, ICON_DASH, ICON_API, ICON_TOGGLE

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
    try:
        xcom_active = (dl.global_config.get("xcom") or {}).get("active", False)  # type: ignore
        xcom_src    = "FILE"
    except Exception:
        xcom_active, xcom_src = False, "—"
    write_line(f"{ICON_TOGGLE} XCOM Active  : {'ON' if xcom_active else 'OFF'}   [{xcom_src}]")
