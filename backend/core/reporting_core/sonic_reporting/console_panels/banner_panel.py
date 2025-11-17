# backend/core/monitor_core/utils/banner.py
from __future__ import annotations

import socket
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from backend.core.common.path_utils import resolve_mother_db_path, is_under_repo
from backend.core.config_core import sonic_config_bridge as C
from backend.core import config_oracle as ConfigOracle
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_live_status

_console = Console()


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


def _fmt_profit(val: Any) -> str:
    if val is None:
        return "–"
    try:
        return f"{float(val):.2f}"
    except Exception:
        return str(val)


def emit_config_banner(env_path: str, db_path_hint: str, dl: Any | None = None) -> None:
    """
    Startup banner for Sonic Monitor.

    Prefers ConfigOracle for monitor config (loop time, enabled flags,
    liquidation thresholds, profit thresholds) and falls back to the older
    JSON-only sonic_config_bridge helpers if Oracle is unavailable.

    Output is rendered as a set of Rich tables instead of raw print lines.
    """
    C.load()  # still used for market helpers and as a fallback

    # Defaults in case Oracle import fails
    loop_s: int = 30
    enabled: dict[str, bool] = {
        "sonic": True,
        "liquid": True,
        "profit": True,
        "market": True,
    }
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
        loop_s = C.get_loop_seconds()
        enabled = C.get_enabled_monitors()
        lq_thr = C.get_liquid_thresholds()
        lq_blast = C.get_liquid_blasts()
        market = C.get_market_config()
        profit = C.get_profit_config()
        cfg_source_label = "FILE"

    # DB + provenance
    resolved_db, prov = resolve_mother_db_path()
    db_exists = resolved_db.exists()
    under_repo = is_under_repo(resolved_db)
    existence = "exists" if db_exists else "MISSING"
    scope = "inside repo" if under_repo else "OUTSIDE repo"

    # Global snooze via Oracle: if not set or <=0, treat as disabled.
    try:
        gcfg = ConfigOracle.get_global_monitor_config()
        snooze_s = int(getattr(gcfg, "global_snooze_seconds", 0) or 0)
    except Exception:
        snooze_s = 0
    snooze_label = f"{snooze_s}s" if snooze_s > 0 else "disabled"

    # XCom + dashboards
    lan_ip = _lan_ip()
    xcom_active, xcom_src = _read_xcom_status(dl)

    dash_local = "http://127.0.0.1:5001/dashboard"
    dash_lan = f"http://{lan_ip}:5001/dashboard"
    api_lan = f"http://{lan_ip}:5000"

    using_oracle = cfg_source_label.startswith("🧙")
    liq_src = "🧙 Oracle (config)" if using_oracle else "FILE (config)"
    prov_cfg_label = "🧙 Oracle" if using_oracle else "FILE"

    # ── Header ────────────────────────────────────────────────────────────────
    _console.print()
    _console.rule("[bold]🦔 Sonic Monitor Configuration[/bold]")

    # ── Top-level environment / wiring summary ───────────────────────────────
    info_table = Table(
        show_header=False,
        box=box.SIMPLE_HEAVY,
        expand=True,
        padding=(0, 1),
    )
    info_table.add_column(style="cyan", no_wrap=True)
    info_table.add_column()

    info_table.add_row("🌐 Sonic Dashboard", dash_local)
    info_table.add_row("🌐 LAN Dashboard", dash_lan)
    info_table.add_row("🔌 LAN API", api_lan)
    info_table.add_row(
        "🛰 XCom Active",
        f"{'ON' if xcom_active else 'OFF'}   [{xcom_src}]",
    )
    info_table.add_row(
        "🧭 Configuration",
        f"{cfg_source_label} — {C._CFG_PATH}",
    )
    info_table.add_row(
        "📦 .env (ignored for config)",
        env_path,
    )
    info_table.add_row(
        "🗄️ Database",
        f"{resolved_db}\n(ACTIVE for runtime data, provenance={prov}, {existence}, {scope})",
    )

    info_panel = Panel(
        info_table,
        box=box.SQUARE,
        padding=(0, 1),
    )
    _console.print(info_panel)

    # DB warnings, if any
    if not db_exists:
        _console.print(
            "[yellow]⚠️ mother.db not found. Runtime numbers will be empty. "
            "Create/seed DB or point MOTHER_DB_PATH correctly.[/]"
        )
    if not under_repo:
        _console.print(
            "[yellow]⚠️ DB path points outside this repo. "
            "Verify backend & monitor are using the SAME file.[/]"
        )

    # ── Runtime + monitor enablement ─────────────────────────────────────────
    runtime_table = Table(
        show_header=False,
        box=box.MINIMAL,
        expand=True,
        padding=(0, 1),
    )
    runtime_table.add_column(style="cyan", no_wrap=True)
    runtime_table.add_column()

    runtime_table.add_row(
        "⚙️ Runtime",
        f"Poll Interval={loop_s}s   Loop Mode=Live   Snooze={snooze_label}",
    )
    runtime_table.add_row(
        "📡 Monitors",
        "Sonic={sonic}   Liquid={liquid}   Profit={profit}   Market={market}".format(
            sonic="ON" if enabled.get("sonic") else "OFF",
            liquid="ON" if enabled.get("liquid") else "OFF",
            profit="ON" if enabled.get("profit") else "OFF",
            market="ON" if enabled.get("market") else "OFF",
        ),
    )

    _console.print(runtime_table)

    # ── Liquidation thresholds ───────────────────────────────────────────────
    liq_table = Table(
        title=f"💧 Liquidation (per-asset)   [source: {liq_src}]",
        box=box.MINIMAL_DOUBLE_HEAD,
        expand=True,
        padding=(0, 1),
    )
    liq_table.add_column("Asset", style="cyan", no_wrap=True)
    liq_table.add_column("Threshold", justify="right")
    liq_table.add_column("Blast", justify="right")

    for asset, icon in (("BTC", "🟡"), ("ETH", "🔷"), ("SOL", "🟣")):
        thr = float(lq_thr.get(asset, 0) or 0)
        bl = int(lq_blast.get(asset, 0) or 0)
        liq_table.add_row(f"{icon} {asset}", f"{thr:.2f}", str(bl))

    _console.print(liq_table)

    # ── Profit monitor thresholds ────────────────────────────────────────────
    pos = profit.get("position_usd", None)
    pf = profit.get("portfolio_usd", None)

    profit_table = Table(
        title=f"💰 Profit Monitor   [source: {liq_src}]",
        box=box.MINIMAL,
        expand=True,
        padding=(0, 1),
    )
    profit_table.add_column("Metric", style="cyan")
    profit_table.add_column("USD", justify="right")

    profit_table.add_row("Position Profit", _fmt_profit(pos))
    profit_table.add_row("Portfolio Profit", _fmt_profit(pf))

    _console.print(profit_table)

    # ── Market monitor summary ───────────────────────────────────────────────
    market_table = Table(
        title="📈 Market Monitor   [source: DB (runtime)]",
        box=box.MINIMAL,
        expand=True,
        padding=(0, 1),
    )
    market_table.add_column("Setting", style="cyan")
    market_table.add_column("Value")

    market_table.add_row(
        "Re-arm",
        (market.get("rearm_mode", "ladder") or "ladder").capitalize(),
    )
    market_table.add_row("Reset", "available")

    _console.print(market_table)

    # ── Provenance footer ────────────────────────────────────────────────────
    footer = Text(
        f"Provenance: [{prov_cfg_label}]=sonic_monitor_config.json (CONFIG) | "
        "[DB]=mother.db (RUNTIME DATA)",
        style="dim",
    )
    _console.print(footer)
    _console.rule()
