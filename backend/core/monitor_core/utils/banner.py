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

    sid = (
        os.getenv("TWILIO_SID")
        or os.getenv("TWILIO_ACCOUNT_SID")
        or "–"
    )
    from_ = (
        os.getenv("TWILIO_FROM")
        or os.getenv("TWILIO_FROM_PHONE")
        or "–"
    )
    to_ = (
        os.getenv("TWILIO_TO")
        or os.getenv("TWILIO_TO_PHONE")
        or os.getenv("TWILIO_DEFAULT_TO")
        or "–"
    )
    print(f"   📞 Twilio      : sid={sid[:3]}… • from={from_} • to={to_}")
    print("══════════════════════════════════════════════════════════════")
