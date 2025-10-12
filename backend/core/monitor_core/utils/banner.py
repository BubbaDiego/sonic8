from __future__ import annotations

import os
from typing import Any


def _mask(s: str, left: int = 3, right: int = 2) -> str:
    if not s or s == "–":
        return "–"
    if len(s) <= left + right:
        return s
    return f"{s[:left]}…{s[-right:]}"


def emit_config_banner(dl: Any, interval_s: int | None) -> None:
    """
    One-time configuration banner (sonic6 parity):
      • Root / DB path / .env
      • Twilio (sys) + Twilio (env) presence snapshot
      • RPC / Helius presence / Perps Program ID
    """
    root = getattr(dl, "root", lambda: os.getcwd())()
    # Be forgiving about how db path is exposed
    db_path = getattr(getattr(dl, "db", None), "db_path", "") or os.path.join(
        os.getcwd(), "backend", "mother.db"
    )
    env_path = getattr(dl, "env_path", lambda: "not found")()

    # Twilio (system snapshot via DataLocker)
    sys_twilio = getattr(
        dl,
        "twilio_system",
        lambda: type(
            "T",
            (),
            {
                "enabled": False,
                "sid": "–",
                "token": "–",
                "from_": "–",
                "to": [],
                "flow": "–",
            },
        )(),
    )()
    # Twilio (env presence only)
    env_twilio = type(
        "E",
        (),
        {
            "sid": os.getenv("TWILIO_ACCOUNT_SID")
            or os.getenv("TWILIO_SID")
            or "–",
            "token": os.getenv("TWILIO_AUTH_TOKEN")
            or os.getenv("TWILIO_TOKEN")
            or "–",
            "from_": os.getenv("TWILIO_FROM_PHONE")
            or os.getenv("TWILIO_FROM")
            or "–",
            "to": os.getenv("TWILIO_TO_PHONE") or "–",
        },
    )()

    rpc = (
        os.getenv("PERP_RPC_URL")
        or os.getenv("ANCHOR_PROVIDER_URL")
        or os.getenv("RPC")
        or ""
    )
    helius_present = bool(os.getenv("HELIUS_API_KEY"))
    perps_program = os.getenv("PERPS_PROGRAM_ID") or ""

    print("────────────────────────────────── ⚙️  Configuration ──────────────────────────────────")
    print(f"📦 Root          : {root}")
    print(f"🗃  Database      : {db_path} ({os.path.basename(db_path) if db_path else ''})")
    print(f"🧾 .env          : {env_path}")
    if interval_s is not None:
        print(f"⏱  Poll Interval : {interval_s}s")
    print(
        "📞 Twilio (sys)  : "
        f"enabled={getattr(sys_twilio, 'enabled', False)} "
        f"| sid={_mask(getattr(sys_twilio, 'sid', '–'))} "
        f"| token={_mask(getattr(sys_twilio, 'token', '–'))} "
        f"| from={_mask(getattr(sys_twilio, 'from_', '–'))} "
        f"| to={[ _mask(x) for x in getattr(sys_twilio, 'to', []) ]} "
        f"| flow={_mask(getattr(sys_twilio, 'flow', '–'))}"
    )
    print(
        f"📞 Twilio (env)  : sid={_mask(getattr(env_twilio, 'sid', '–'))} "
        f"| token={_mask(getattr(env_twilio, 'token', '–'))} "
        f"| from={_mask(getattr(env_twilio, 'from_', '–'))} "
        f"| to={_mask(getattr(env_twilio, 'to', '–'))}"
    )
    print(f"🌐 RPC           : {rpc or '–'}")
    print(f"🔑 Helius key    : {'✓' if helius_present else '–'}")
    print(f"📜 Perps ProgID  : {perps_program or '–'}")
    print("──────────────────────────────────────────────────────────────────────────────────────")
