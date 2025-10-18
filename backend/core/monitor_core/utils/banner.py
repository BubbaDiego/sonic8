from __future__ import annotations

from backend.core.config_core import sonic_config_bridge as C


def emit_config_banner(env_path: str, db_path: str) -> None:
    C.load()

    loop_s   = C.get_loop_seconds()
    enabled  = C.get_enabled_monitors()
    lq_thr   = C.get_liquid_thresholds()
    lq_blast = C.get_liquid_blasts()
    market   = C.get_market_config()
    profit   = C.get_profit_config()

    print("══════════════════════════════════════════════════════════════")
    print("   🦔 Sonic Monitor Configuration")
    print("══════════════════════════════════════════════════════════════")
    print("🌐 Sonic Dashboard: http://127.0.0.1:5001/dashboard")
    print("🔒 Muted Modules:      ConsoleLogger, console_logger, LoggerControl, werkzeug, uvicorn.access, fuzzy_wuzzy, asyncio")
    print(f"🧭 Configuration: JSON ONLY — {C._CFG_PATH}")            # CONFIG from FILE
    print(f"📦 .env (ignored for config) : {env_path}")             # ENV ignored for CONFIG
    print(f"🔌 Database       : {db_path} (ACTIVE for runtime data)")  # DB ACTIVE

    print()
    print(f"⚙️ Runtime        : Poll Interval={loop_s}s   Loop Mode=Live   Snooze=disabled")
    print()
    print(f"📡 Monitors       : Sonic={'ON' if enabled.get('sonic') else 'OFF'}   "
          f"Liquid={'ON' if enabled.get('liquid') else 'OFF'}   "
          f"Profit={'ON' if enabled.get('profit') else 'OFF'}   "
          f"Market={'ON' if enabled.get('market') else 'OFF'}")

    print()
    print("💧 Liquidation (per-asset)   [source: FILE (config)]")
    for asset, icon in (("BTC", "🟡"), ("ETH", "🔷"), ("SOL", "🟣")):
        thr = float(lq_thr.get(asset, 0) or 0)
        bl  = int(lq_blast.get(asset, 0) or 0)
        print(f"  {icon} {asset:<3} Threshold: {thr:.2f}    Blast: {bl}")

    print()
    print("💰 Profit Monitor           [source: DB (runtime)]")
    pos = profit.get("position_usd", None)
    pf  = profit.get("portfolio_usd", None)
    print(f"  Position Profit (USD) : {pos if pos is not None else '–'}")
    print(f"  Portfolio Profit (USD): {pf if pf is not None else '–'}")

    print()
    print("📈 Market Monitor          [source: DB (runtime)]")
    print(f"  Re-arm: {market.get('rearm_mode','ladder').capitalize()}   Reset: available")

    print()
    print("Provenance: [FILE]=sonic_monitor_config.json (CONFIG) | [DB]=mother.db (RUNTIME DATA)")
    print("══════════════════════════════════════════════════════════════")
