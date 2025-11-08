# backend/core/webterm_core/autostart.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .manager import ensure_running

CONFIG_PATH = Path("backend/config/webterm_config.json")

DEFAULT_CFG: Dict[str, Any] = {
    "enabled": True,
    "autostart": True,
    "provider": "cloudflare",     # "cloudflare" | "tailscale" | "none"
    "port": 7681,
    "command": r"C:\\sonic7\\.venv\\Scripts\\python.exe C:\\sonic7\\launch_pad.py ; pwsh",
    "auth": {
        "basic_user": "geno",
        "basic_pass": "change-this"
    },
    "cloudflare": {
        "mode": "quick",          # "quick" prints ephemeral trycloudflare URL automatically
        "hostname": None,         # for named tunnels, set e.g. "sonic.example.com"
        "tunnel_name": None
    },
    "qr": {
        "enabled": True,
        "border": 1               # quiet-zone pixels around QR
    }
}

def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out

def _read_json_file(path: Path) -> Optional[Dict]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _write_json_file(path: Path, obj: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    except Exception:
        pass

def _load_cfg_from_file() -> Dict[str, Any]:
    cfg = _read_json_file(CONFIG_PATH)
    if cfg is None:
        # First run: create default config for the user to edit
        _write_json_file(CONFIG_PATH, DEFAULT_CFG)
        cfg = dict(DEFAULT_CFG)
    return cfg

def _make_qr_ascii(data: str, border: int = 1) -> Optional[str]:
    """
    Return a Unicode block ('██' / '  ') QR string if the 'qrcode' package is installed.
    Otherwise return None (caller will just print the link).
    """
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except Exception:
        return None

    qr = qrcode.QRCode(
        version=None,                # auto-fit
        error_correction=ERROR_CORRECT_M,
        box_size=1,
        border=max(0, int(border or 0)),
    )
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()

    # Build double-width blocks for decent aspect ratio in console
    full = "██"
    empty = "  "
    lines = []
    for row in matrix:
        lines.append("".join(full if cell else empty for cell in row))
    return "\n".join(lines)

def autostart(dl: Any = None, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """
    Read ONLY from backend/config/webterm_config.json.
    Start web terminal if enabled+autostart; print a link (and QR if available).
    """
    log = logger or logging.getLogger("webterm")

    file_cfg = _load_cfg_from_file()
    cfg = _merge(DEFAULT_CFG, file_cfg or {})

    if not cfg.get("enabled", True) or not cfg.get("autostart", True):
        return None

    url = ensure_running(cfg, dl=dl, logger=log)

    # --- Output banner (with optional QR) ---
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich.align import Align
        console = Console()

        if url:
            qr_cfg = cfg.get("qr", {}) or {}
            qr_txt = _make_qr_ascii(url, border=qr_cfg.get("border", 1)) if qr_cfg.get("enabled", True) else None

            if qr_txt:
                body = f"{qr_txt}\n\n{url}"
                console.print(
                    Panel.fit(
                        Align.center(Text(body, style="green")),
                        title="Web Terminal (QR)",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel.fit(
                        Text(f"🌐 Web Terminal: {url}", style="bold cyan"),
                        title="Sonic",
                        border_style="cyan",
                    )
                )
        else:
            console.print(
                Panel.fit(
                    Text("🌐 Web Terminal: starting…", style="bold yellow"),
                    title="Sonic",
                    border_style="yellow",
                )
            )
    except Exception:
        print(f"[Sonic] Web Terminal: {url or 'starting…'}")

    return url
