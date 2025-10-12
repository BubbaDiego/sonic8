from __future__ import annotations

from typing import Any, List

from backend.core.reporting_core.prelaunch import print_prelaunch_body
from backend.core.reporting_core.console_reporter import emit_dashboard_link


def emit_config_banner(
    dl: Any,
    interval_s: int,
    *,
    muted_modules: List[str] | None = None,
    xcom_live: bool = True,
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
    # === Then the detailed pre-launch body ===
    print_prelaunch_body(dl, interval_s, xcom_live=xcom_live)
    print("══════════════════════════════════════════════════════════════")
