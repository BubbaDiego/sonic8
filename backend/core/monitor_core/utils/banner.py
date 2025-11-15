from __future__ import annotations

import socket

from typing import Any, Tuple

from backend.core.common.path_utils import resolve_mother_db_path, is_under_repo
from backend.core.config_core import sonic_config_bridge as C


def emit_config_banner(env_path: str, db_path_hint: str, dl: Any | None = None) -> None:
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

    def _coerce_bool(value: Any) -> Tuple[bool | None, bool]:
        if isinstance(value, bool):
            return value, True
        if isinstance(value, (int, float)):
            return bool(value), True
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "on", "yes"}:
                return True, True
            if lowered in {"false", "0", "off", "no"}:
                return False, True
        return None, False

    def _read_xcom_status() -> tuple[bool, str]:
        active: bool | None = None
        src = "—"

        # Prefer configuration file
        try:
            cfg = C.load()
        except Exception:
            cfg = {}
        xcom_section: Any = {}
        if isinstance(cfg, dict):
            xcom_section = cfg.get("xcom")
            if not xcom_section:
                monitor_cfg = cfg.get("monitor") or {}
                if isinstance(monitor_cfg, dict):
                    xcom_section = monitor_cfg.get("xcom") or monitor_cfg.get("xcom_live")
        if isinstance(xcom_section, dict):
            if "live" in xcom_section:
                active = bool(xcom_section.get("live"))
                src = "FILE"
            elif "enabled" in xcom_section:
                active = bool(xcom_section.get("enabled"))
                src = "FILE"
        elif xcom_section is not None:
            coerced, ok = _coerce_bool(xcom_section)
            if ok:
                active, src = coerced, "FILE"
        if active is None:
            try:
                active = bool(C.get_xcom_live())
                src = "FILE"
            except Exception:
                active = None

        # Fall back to runtime database via DataLocker
        if active is None and dl is not None:
            try:
                gconf = getattr(dl, "global_config", None)
            except Exception:
                gconf = None
            if gconf and hasattr(gconf, "get"):
                try:
                    g_val = gconf.get("xcom")  # type: ignore[attr-defined]
                except Exception:
                    g_val = None
                if isinstance(g_val, dict):
                    if "live" in g_val:
                        active = bool(g_val.get("live"))
                        src = "FILE"
                    elif "enabled" in g_val:
                        active = bool(g_val.get("enabled"))
                        src = "FILE"
                elif g_val is not None:
                    coerced, ok = _coerce_bool(g_val)
                    if ok:
                        active = coerced
                        src = "FILE"

            try:
                system = getattr(dl, "system", None)
            except Exception:
                system = None
            if active is None and system is not None:
                try:
                    raw = system.get_var("xcom")
                except Exception:
                    raw = None
                if raw is None:
                    for key in ("xcom_live", "xcom_config"):
                        try:
                            raw = system.get_var(key)
                        except Exception:
                            raw = None
                        if raw is not None:
                            break
                if isinstance(raw, dict):
                    if "live" in raw:
                        active = bool(raw.get("live"))
                        src = "DB"
                    elif "enabled" in raw:
                        active = bool(raw.get("enabled"))
                        src = "DB"
                elif raw is not None:
                    coerced, ok = _coerce_bool(raw)
                    if ok:
                        active = coerced
                        src = "DB"

        if active is None:
            active = False
        return bool(active), src

    xcom_active, xcom_src = _read_xcom_status()
    print(f"🛰 XCOM Active  : {'ON' if xcom_active else 'OFF'}   [{xcom_src}]")
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
    print("💰 Profit Monitor           [source: FILE (config)]")
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
    print("Provenance: [FILE]=sonic_monitor_config.json (CONFIG) | [DB]=mother.db (RUNTIME DATA)")
    print("══════════════════════════════════════════════════════════════")
