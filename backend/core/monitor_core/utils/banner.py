from __future__ import annotations

from backend.core.common.path_utils import resolve_mother_db_path, is_under_repo
from backend.core.config_core import sonic_config_bridge as C


def emit_config_banner(env_path: str, db_path_hint: str) -> None:
    C.load()

    loop_s   = C.get_loop_seconds()
    enabled  = C.get_enabled_monitors()
    lq_thr   = C.get_liquid_thresholds()
    lq_blast = C.get_liquid_blasts()
    market   = C.get_market_config()
    profit   = C.get_profit_config()

    resolved_db, prov = resolve_mother_db_path()
    db_exists = resolved_db.exists()
    under_repo = is_under_repo(resolved_db)
    existence = "exists" if db_exists else "MISSING"
    scope = "inside repo" if under_repo else "OUTSIDE repo"

    print("══════════════════════════════════════════════════════════════")
    print("   🦔 Sonic Monitor Configuration")
    print("══════════════════════════════════════════════════════════════")
    print("🌐 Sonic Dashboard: http://127.0.0.1:5001/dashboard")
    print("🔒 Muted Modules:      ConsoleLogger, console_logger, LoggerControl, werkzeug, uvicorn.access, fuzzy_wuzzy, asyncio")
    print(f"🧭 Configuration: JSON ONLY — {C._CFG_PATH}")            # CONFIG from FILE
    print(f"📦 .env (ignored for config) : {env_path}")             # ENV ignored for CONFIG
    print(
        f"🔌 Database       : {resolved_db}  "
        f"(ACTIVE for runtime data, provenance={prov}, {existence}, {scope})"
    )  # DB ACTIVE
    if not db_exists:
        print(
            "⚠️  mother.db not found. Runtime numbers will be empty. Create/seed DB or point "
            "MOTHER_DB_PATH correctly."
        )
    if not under_repo:
        print(
            "⚠️  DB path points outside this repo. Verify backend & monitor are using the SAME file."
        )

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
