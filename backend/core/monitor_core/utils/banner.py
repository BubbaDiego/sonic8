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
    print("──────────────────────────────────────────────────────────────")

    def _true(key: str, default: bool = False) -> bool:
        value = os.getenv(key)
        if value is None:
            return default
        return str(value).strip().lower() not in {"0", "false", "no", "", "none"}

    def _float_env(key: str, default: float) -> float:
        raw = os.getenv(key)
        if raw in (None, ""):
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    enabled_liquid = _true("ENABLED_LIQUID", True)
    enabled_profit = _true("ENABLED_PROFIT", True)
    enabled_market = _true("ENABLED_MARKET", False)
    enabled_price = _true("ENABLED_PRICE", False)
    liquid_dist_pct = _float_env("LIQUID_DIST_PCT", 8.0)
    profit_pos = _float_env("PROFIT_POS", 75.0)
    profit_pf = _float_env("PROFIT_PF", 200.0)

    monitors_line = (
        f"liquid={'on' if enabled_liquid else 'off'}({liquid_dist_pct:.1f}%) • "
        f"profit={'on' if enabled_profit else 'off'}(pos={profit_pos:.0f}%, pf=${profit_pf:.0f}) • "
        f"market={'on' if enabled_market else 'off'} • "
        f"price={'on' if enabled_price else 'off'}"
    )

    assets_env = os.getenv("SONIC_PRICE_ASSETS", "BTC,ETH,SOL")
    assets = [token.strip().upper() for token in assets_env.split(",") if token.strip()]
    if len(assets) > 6:
        assets_display = ", ".join(assets[:6]) + f", +{len(assets) - 6} more"
    else:
        assets_display = ", ".join(assets) if assets else "–"

    position_src = (os.getenv("SONIC_POSITIONS_SOURCE", "dl") or "dl").lower()
    sync_on_empty = _true("SONIC_SYNC_ON_EMPTY", False)

    print(f"   🔧 Monitors     : {monitors_line}")
    print(f"   🪙 Price Assets : {assets_display}")
    print(
        "   📈 Position src : "
        f"{position_src} (sync_on_empty={'on' if sync_on_empty else 'off'})"
    )
    print("══════════════════════════════════════════════════════════════")
