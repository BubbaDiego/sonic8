from __future__ import annotations

import os
from typing import Any


def emit_config_banner(dl: Any, interval_s: int) -> None:
    print("══════════════════════════════════════════════════════════════")
    print("   🦔 Sonic Monitor Configuration")
    print("══════════════════════════════════════════════════════════════")
    print(f"   🕒 Poll Interval : {interval_s}s")
    db_path = getattr(getattr(dl, "db", None), "db_path", None) if dl else None
    print(f"   🗄️  Database Path : {db_path or '–'}")
    # keep banner minimal but useful (sonic6 vibe)
    env_path = os.getenv("SONIC_ENV_PATH_RESOLVED")
    if not env_path:
        env_path_getter = getattr(dl, "env_path", None)
        try:
            env_path = env_path_getter() if callable(env_path_getter) else env_path_getter
        except Exception:
            env_path = None
    print(f"   📦 .env        : {env_path or '–'}")
    tw_sid = os.getenv("TWILIO_SID", "–")
    tw_from = os.getenv("TWILIO_FROM", "–")
    tw_to = os.getenv("TWILIO_TO", "–")
    print(f"   📞 Twilio      : sid={tw_sid[:3]}… • from={tw_from} • to={tw_to or '–'}")
    print("══════════════════════════════════════════════════════════════")
