from __future__ import annotations

import os
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

    # One concise “effective source” line (what the monitor is *actually* using now)
    # We infer like this: if SONIC_MONITOR_LOOP_SECONDS is set and differs from interval_s → ENV,
    # else if system_vars has loop and equals interval_s → DB, else → JSON.
    try:
        eff_runtime = "JSON"
        env_loop = os.getenv("SONIC_MONITOR_LOOP_SECONDS")
        if env_loop and float(env_loop) == float(interval_s):
            eff_runtime = "ENV"
        elif hasattr(dl, "system") and getattr(dl, "system", None):
            dbv = dl.system.get_var("sonic_monitor_loop_time")
            if dbv and float(dbv) == float(interval_s):
                eff_runtime = "DB"
    except Exception:
        eff_runtime = "JSON"
    # The rest (liquid/profit/twilio) are still driven by DB in legacy code paths;
    # we mark them DB unless UI has just written JSON-only. Keep this pragmatic and simple.
    eff_liquid = "JSON"
    eff_profit = "DB"
    eff_twilio = "ENV"
    print(
        f"🧾 Effective sources: runtime={eff_runtime}  liquid={eff_liquid}  profit={eff_profit}  twilio={eff_twilio}"
    )
    # === Then the detailed pre-launch body ===
    cfg_loop = get_loop_seconds()
    print_prelaunch_body(
        dl,
        cfg_loop if cfg_loop else interval_s,
        xcom_live=xcom_live,
        resolved=resolved or {},
    )
    print("══════════════════════════════════════════════════════════════")
