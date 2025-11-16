# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

from backend.core.reporting_core.sonic_reporting.config_probe import discover_json_path, parse_json
from backend.core.reporting_core.sonic_reporting.xcom_extras import xcom_live_status


def _get(dl: Any, *names: str, default: Any = None) -> Any:
    """Safely fetch an attribute or dict key from dl."""
    if dl is None:
        return default
    for n in names:
        # dict-like
        if isinstance(dl, dict) and n in dl:
            return dl[n]
        # attr-like
        if hasattr(dl, n):
            try:
                return getattr(dl, n)
            except Exception:
                continue
    return default


def _chip_on_off(val: Optional[bool]) -> Text:
    if val is True:
        return Text("🟢  ON", style="green")
    if val is False:
        return Text("🔴  OFF", style="red")
    return Text("—", style="dim")


def _title(console: Console) -> None:
    title = Text.assemble(
        Text("🦔  ", style="bold"),
        Text("Sonic Monitor Configuration", style="bold cyan"),
    )
    console.print(title)
    console.rule(style="cyan")


def render(dl: Any, csum: Any, default_json_path: Optional[str] = None) -> None:
    """
    Sequencer contract: render(dl, csum, default_json_path=None)

    Minimal, import-safe banner:
    - No raw Windows backslashes in literals (use forward slashes in fallbacks).
    - All dynamic values are converted with str() at render time.
    """
    console = Console()
    _title(console)

    # URLs (prefer dl, then safe fallbacks)
    dash_local = _get(dl, "dashboard_url", "dashboard_local", default="http://127.0.0.1:5001/dashboard")
    dash_lan   = _get(dl, "dashboard_url_lan", "dashboard_lan", default="http://10.0.0.2:5001/dashboard")
    api_lan    = _get(dl, "api_url_lan", "api_lan", default="http://10.0.0.2:5000")

    # XCOM state — resolve exactly like XCOM Check (ENV → DB → FILE)
    cfg = {}
    try:
        path = default_json_path or discover_json_path(None)
        if path:
            cfg_obj, err, meta = parse_json(path)
            if isinstance(cfg_obj, dict):
                cfg = cfg_obj
    except Exception:
        cfg = {}
    try:
        xcom_live, live_src = xcom_live_status(dl, cfg=cfg)
    except Exception:
        xcom_live, live_src = False, "—"
    muted = _get(dl, "muted_modules", default=None)

    # Paths (shown as values only; we never embed raw backslashes here)
    cfg_path = _get(
        dl,
        "config_path",
        "config_file",
        default=(default_json_path or "C:/sonic8/backend/config/sonic_monitor_config.json"),
    )
    env_path = _get(dl, "env_path", "env_file", default="C:/sonic8/.env")
    db_path  = _get(dl, "db_path", "database_path", default="C:/sonic8/backend/mother.db")

    # Monitor config
    mon_cfg = cfg.get("monitor") if isinstance(cfg, dict) else None
    mon_cfg = mon_cfg if isinstance(mon_cfg, dict) else {}
    poll = mon_cfg.get("loop_seconds")
    try:
        poll = int(poll) if poll is not None else 30
    except Exception:
        poll = 30

    loop_mode = (
        str(mon_cfg.get("loop_mode") or _get(dl, "loop_mode", default="Live") or "Live").strip()
        or "Live"
    )

    # Global snooze from config (monitor.global_snooze_seconds)
    raw_snooze = mon_cfg.get("global_snooze_seconds", 0)
    try:
        global_snooze = int(raw_snooze or 0)
    except Exception:
        global_snooze = 0

    # These mirror what XCom bridge uses as hard defaults if config is 0/missing.
    hard_default_liquid = 600
    hard_default_profit = 1200

    if global_snooze > 0:
        snooze_txt = f"{global_snooze}s [FILE]"
    else:
        snooze_txt = f"disabled [DEFAULT={hard_default_liquid}s/{hard_default_profit}s]"

    # Build a borderless table (matches your style)
    t = Table(
        show_header=True,
        header_style="bold",
        show_lines=False,
        box=None,
        pad_edge=False,
        expand=False,
    )
    t.add_column("Activity", justify="left",  no_wrap=False)
    t.add_column("Status",   justify="left",  no_wrap=True)
    t.add_column("Details",  justify="left",  no_wrap=False)

    t.add_row("🌐  Sonic Dashboard", " ", Text(str(dash_local)))
    t.add_row("🌐  LAN Dashboard",   " ", Text(str(dash_lan)))
    t.add_row("🔱  LAN API",         " ", Text(str(api_lan)))
    t.add_row("📡  XCOM Live", _chip_on_off(bool(xcom_live)), Text(f"[{live_src}]"))
    t.add_row("🔒  Muted Modules", "—" if not muted else "…", "—" if not muted else Text(str(muted)))
    t.add_row("🟡  Configuration", "FILE", Text(str(cfg_path)))
    t.add_row("🧪  .env (ignored)", " ",   Text(str(env_path)))
    t.add_row("🗄️  Database", Text("ACTIVE for runtime data", style="cyan"), Text(str(db_path)))

    console.print(t)
    runtime_line = (
        f"⚙️ Runtime        : Poll Interval={poll}s   "
        f"Loop Mode={loop_mode}   Snooze={snooze_txt}"
    )
    console.print(runtime_line)


# Sequencer alternate import symbol
panel = render
