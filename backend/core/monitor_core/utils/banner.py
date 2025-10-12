from __future__ import annotations

from typing import Any, List
import os
from backend.core.reporting_core.prelaunch import print_prelaunch_body
from backend.core.reporting_core.console_reporter import emit_dashboard_link


def emit_config_banner(dl: Any, interval_s: int, *, muted_modules: List[str] | None = None) -> None:
    print("══════════════════════════════════════════════════════════════")
    print("   🦔 Sonic Monitor Configuration")
    print("══════════════════════════════════════════════════════════════")
    # Print the full pre-launch body inside the banner (one-time)
    print_prelaunch_body(dl, interval_s)
    link_flag = os.getenv("SONIC_MONITOR_DASHBOARD_LINK", "1").strip().lower()
    if link_flag not in {"0", "false", "off", "no"}:
        host = os.getenv("SONIC_DASHBOARD_HOST", "127.0.0.1")
        route = os.getenv("SONIC_DASHBOARD_ROUTE", "/dashboard")
        port_env = os.getenv("SONIC_DASHBOARD_PORT", "5001")
        try:
            port = int(port_env)
        except ValueError:
            port = 5001
        try:
            emit_dashboard_link(host=host, port=port, route=route)
        except Exception:
            pass
    if muted_modules is not None:
        m = ", ".join(muted_modules) if muted_modules else "–"
        print(f"🔒 Muted Modules:      {m}")
    print("══════════════════════════════════════════════════════════════")
