from __future__ import annotations

from typing import Any

from backend.core.reporting_core.prelaunch import print_prelaunch_body


def emit_config_banner(dl: Any, interval_s: int) -> None:
    print("══════════════════════════════════════════════════════════════")
    print("   🦔 Sonic Monitor Configuration")
    print("══════════════════════════════════════════════════════════════")
    # Print the full pre-launch body inside the banner (one-time)
    print_prelaunch_body(dl, interval_s)
    print("══════════════════════════════════════════════════════════════")
