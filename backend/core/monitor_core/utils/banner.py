from __future__ import annotations

from typing import Any, List, Dict, Tuple

from backend.core.reporting_core.prelaunch import print_prelaunch_body
from backend.core.reporting_core.console_reporter import emit_dashboard_link
from backend.core.config_core.sonic_config_bridge import get_loop_seconds


def emit_config_banner(
    dl: Any,
    interval_s: int,
    *,
    muted_modules: List[str] | None = None,
    xcom_live: bool = True,
    resolved: Dict | None = None,
    config_source: Tuple[str, str] | None = None,
) -> None:
    print("══════════════════════════════════════════════════════════════")
    print("   🦔 Sonic Monitor Configuration")
    print("══════════════════════════════════════════════════════════════")
    # === Top lines first ===
    try:
        emit_dashboard_link()
    except Exception:
        pass
    if muted_modules is not None:
        m = ", ".join(muted_modules) if muted_modules else "–"
        print(f"🔒 Muted Modules:      {m}")
    if config_source:
        src, note = config_source
        if src == "JSON" and note:
            print(f"🧭 Configuration: {src} ({note})")
        elif note:
            print(f"🧭 Configuration: {src} — {note}")
        else:
            print(f"🧭 Configuration: {src}")
    # === Then the detailed pre-launch body ===
    cfg_loop = get_loop_seconds()
    print_prelaunch_body(
        dl,
        cfg_loop if cfg_loop else interval_s,
        xcom_live=xcom_live,
        resolved=resolved or {},
    )
    print("══════════════════════════════════════════════════════════════")
