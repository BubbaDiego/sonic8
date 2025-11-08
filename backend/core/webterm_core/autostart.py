from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional

from .manager import ensure_running, _read_json

DEFAULT_CFG = {
    "enabled": True,
    "autostart": True,
    "provider": "cloudflare",        # "cloudflare" | "tailscale" | "none"
    "port": 7681,
    "command": r"C:\\sonic7\\.venv\\Scripts\\python.exe C:\\sonic7\\launch_pad.py",
    "auth": {
        "basic_user_env": "SONIC_WEBTERM_USER",
        "basic_pass_env": "SONIC_WEBTERM_PASS",
    },
    "cloudflare": {
        "mode": "named",             # "named" | "quick"
        "hostname": None,            # e.g. "sonic.example.com"
        "tunnel_name": None          # optional; if omitted, derived from hostname prefix
    },
}

def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out

def _load_cfg_from_dl(dl: Any) -> Optional[Dict]:
    # Best-guess places people store feature flags;
    # falls back to JSON state if not present.
    try:
        if hasattr(dl, "system") and hasattr(dl.system, "get_var"):
            cfg = dl.system.get_var("webterm_config")
            if cfg:
                return cfg
        for name in ("get_system_var", "get_var"):
            if hasattr(dl, name):
                cfg = getattr(dl, name)("webterm_config")
                if cfg:
                    return cfg
    except Exception:
        pass
    return _read_json(None, None)  # noop, kept for signature symmetry

def autostart(dl: Any = None, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """
    Read config (DataLocker or env), ensure web terminal is running, and
    print a one-liner link to stdout (Rich if available).
    """
    log = logger or logging.getLogger("webterm")

    # 1) Resolve config
    cfg = _merge(DEFAULT_CFG, _load_cfg_from_dl(dl) or {})
    # Env overrides (simple):
    if os.environ.get("SONIC_WEBTERM_PROVIDER"):
        cfg["provider"] = os.environ["SONIC_WEBTERM_PROVIDER"].strip().lower()
    if os.environ.get("SONIC_WEBTERM_PORT"):
        try:
            cfg["port"] = int(os.environ["SONIC_WEBTERM_PORT"])
        except Exception:
            pass
    if os.environ.get("SONIC_WEBTERM_AUTOSTART"):
        val = os.environ["SONIC_WEBTERM_AUTOSTART"].strip().lower()
        cfg["autostart"] = val in ("1", "true", "yes", "on")

    if not cfg.get("enabled", True) or not cfg.get("autostart", True):
        return None

    # 2) Start & fetch URL
    url = ensure_running(cfg, dl=dl, logger=log)

    # 3) Print the link line at startup
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        c = Console()
        if url:
            c.print(Panel.fit(Text(f"🌐 Web Terminal: {url}", style="bold cyan"), title="Sonic", border_style="cyan"))
        else:
            c.print(Panel.fit(Text("🌐 Web Terminal: starting…", style="bold yellow"), title="Sonic", border_style="yellow"))
    except Exception:
        print(f"[Sonic] Web Terminal: {url or 'starting…'}")

    return url
