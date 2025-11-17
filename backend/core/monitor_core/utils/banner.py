from __future__ import annotations

import socket

from typing import Any

from backend.core.common.path_utils import resolve_mother_db_path, is_under_repo
from backend.core.config_core import sonic_config_bridge as C
from backend.core import config_oracle as ConfigOracle
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_live_status


def emit_config_banner(env_path: str, db_path_hint: str, dl: Any | None = None) -> None:
    """
    Startup banner for Sonic Monitor.

    This now prefers ConfigOracle for monitor config (loop time, enabled flags,
    liquidation thresholds, profit thresholds) and falls back to the older
    JSON-only sonic_config_bridge helpers if Oracle is unavailable.
    """
    C.load()  # still used for market + Twilio helpers and as a fallback

    # Defaults in case Oracle import fails
    loop_s: int = 30
    enabled: dict[str, bool] = {"sonic": True, "liquid": True, "profit": True, "market": True}
    lq_thr: dict[str, float] = {}
    lq_blast: dict[str, int] = {}
    market: dict[str, Any] = {}
    profit: dict[str, Any] = {}
    cfg_source_label = "FILE"

    # --- Oracle-first view over monitor config ---
    try:
        bundle = ConfigOracle.get_monitor_bundle()
        gcfg = bundle.global_config
        loop_s = int(gcfg.loop_seconds or 30)

        mons = bundle.monitors or {}
        enabled = {name: bool(defn.enabled) for name, defn in mons.items()}

        # Liquidation thresholds / blast from Oracle domain helpers
        lq_thr = ConfigOracle.get_liquid_thresholds()
        lq_blast = ConfigOracle.get_liquid_blast_map()

        # Profit thresholds from Oracle; normalize to the keys this banner expects
        profit_thr = ConfigOracle.get_profit_thresholds()
        profit = {
            "position_usd": profit_thr.get("position_profit_usd"),
            "portfolio_usd": profit_thr.get("portfolio_profit_usd"),
        }

        # Market config is still JSON-only for now
        market = C.get_market_config()

        cfg_source_label = "🧙 Oracle"
    except Exception:
        # Fallback to legacy JSON-only bridge (existing behavior)
        loop_s   = C.get_loop_seconds()
        enabled  = C.get_enabled_monitors()
        lq_thr   = C.get_liquid_thresholds()
        lq_blast = C.get_liquid_blasts()
        market   = C.get_market_config()
        profit   = C.get_profit_config()
        cfg_source_label = "FILE"

    resolved_db, prov = resolve_mother_db_path()
    db_exists = resolved_db.exists()
    under_repo = is_under_repo(resolved_db)
    existence = "exists" if db_exists else "MISSING"
    scope = "inside repo" if under_repo else "OUTSIDE repo"

    print("══════════════════════════════════════════════════════════════")
    print("   🦔 Sonic Monitor Configuration")
    print("══════════════════════════════════════════════════════════════")
    print("🌐 Sonic Dashboard: http://127.0.0.1:5001/dashboard")

    def _lan_ip() -> str:
        """Best-effort detection of a LAN-reachable IP address."""

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if ip.startswith("127."):
                    raise RuntimeError("loopback address")
                return ip
        except Exception:
            try:
                ip = socket.gethostbyname(socket.gethostname())
                if ip and not ip.startswith("127."):
                    return ip
            except Exception:
                pass
        return "127.0.0.1"

    lan_ip = _lan_ip()
    print(f"🌐 LAN Dashboard : http://{lan_ip}:5001/dashboard")
    print(f"🔌 LAN API      : http://{lan_ip}:5000")

    def _read_xcom_status(dl: Any | None = None) -> tuple[bool, str]:
        """
        Resolve XCom "live" status for the banner.

        Delegates to xcom_live_status, which already knows about ENV, DB, and
        ConfigOracle. We then pretty-print the source label in the banner.
        """

        live, src = xcom_live_status(dl or None)
        src_norm = (src or "").upper().strip()
        if src_norm == "ORACLE":
            return bool(live), "🧙 Oracle"
        return bool(live), src_norm or "DEFAULT"

    xcom_active, xcom_src = _read_xcom_status(dl)
    print(f"🛰 XCOM Active  : {'ON' if xcom_active else 'OFF'}   [{xcom_src}]")
    print("🔒 Muted Modules:      ConsoleLogger, console_logger, LoggerControl, werkzeug, uvicorn.access, fuzzy_wuzzy, asyncio")

    # If Oracle resolved monitor config successfully, cfg_source_label will be "🧙 Oracle".
    print(f"🧭 Configuration: {cfg_source_label} — {C._CFG_PATH}")
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

    # Global snooze via Oracle: if not set or <=0, treat as disabled.
    try:
        gcfg = ConfigOracle.get_global_monitor_config()
        snooze_s = int(getattr(gcfg, "global_snooze_seconds", 0) or 0)
    except Exception:
        snooze_s = 0

    snooze_label = f"{snooze_s}s" if snooze_s > 0 else "disabled"

    print(f"⚙️ Runtime        : Poll Interval={loop_s}s   Loop Mode=Live   Snooze={snooze_label}")
    print()
    print(f"📡 Monitors       : Sonic={'ON' if enabled.get('sonic') else 'OFF'}   "
          f"Liquid={'ON' if enabled.get('liquid') else 'OFF'}   "
          f"Profit={'ON' if enabled.get('profit') else 'OFF'}   "
          f"Market={'ON' if enabled.get('market') else 'OFF'}")

    print()
    using_oracle = cfg_source_label.startswith("🧙")
    liq_src = "🧙 Oracle (config)" if using_oracle else "FILE (config)"
    print(f"💧 Liquidation (per-asset)   [source: {liq_src}]")
    for asset, icon in (("BTC", "🟡"), ("ETH", "🔷"), ("SOL", "🟣")):
        thr = float(lq_thr.get(asset, 0) or 0)
        bl  = int(lq_blast.get(asset, 0) or 0)
        print(f"  {icon} {asset:<3} Threshold: {thr:.2f}    Blast: {bl}")

    print()
    print(f"💰 Profit Monitor           [source: {liq_src}]")
    pos = profit.get("position_usd", None)
    pf  = profit.get("portfolio_usd", None)

    def _fmt_profit(val: Any) -> str:
        if val is None:
            return "–"
        try:
            return f"{float(val):.2f}"
        except Exception:
            return str(val)

    print(f"  Position Profit (USD) : {_fmt_profit(pos)}")
    print(f"  Portfolio Profit (USD): {_fmt_profit(pf)}")

    print()
    print("📈 Market Monitor          [source: DB (runtime)]")
    print(f"  Re-arm: {market.get('rearm_mode','ladder').capitalize()}   Reset: available")

    print()
    prov_cfg_label = "🧙 Oracle" if using_oracle else "FILE"
    print(f"Provenance: [{prov_cfg_label}]=sonic_monitor_config.json (CONFIG) | [DB]=mother.db (RUNTIME DATA)")
    print("══════════════════════════════════════════════════════════════")
