from __future__ import annotations

import json
import logging
from math import ceil
from pathlib import Path
from typing import Any, Dict, Optional, List

from .manager import ensure_running

CONFIG_PATH = Path("backend/config/webterm_config.json")

DEFAULT_CFG: Dict[str, Any] = {
    "enabled": True,
    "autostart": True,
    "provider": "cloudflare",     # "cloudflare" | "tailscale" | "none"
    "port": 7681,
    "command": r"C:\\sonic7\\.venv\\Scripts\\python.exe C:\\sonic7\\launch_pad.py ; pwsh",
    "auth": {},                   # no Basic Auth by default (JSON-only control)
    "cloudflare": {
        "mode": "quick",          # "quick" = ephemeral trycloudflare URL
        "hostname": None,         # for named tunnels, e.g. "sonic.example.com"
        "tunnel_name": None
    },
    "qr": {
        "enabled": True,
        "border": 0,              # 0–4 (0/1 keeps the code tight)
        "compact": True,          # half-block mode (▀▄█) ~4x smaller than full blocks
        "max_cols": 44,           # hard cap on QR width (characters) in compact mode
        "color": "green",         # Rich color for QR + frame
        "link_label": "Open Web Terminal"
    }
}

def _merge(a: dict, b: dict) -> dict:
    """Deep merge where empty dicts in `b` override (clear) defaults."""
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = v if not v else _merge(out[k], v)
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
        _write_json_file(CONFIG_PATH, DEFAULT_CFG)  # bootstrap first run
        cfg = dict(DEFAULT_CFG)
    return cfg

# ---------------- QR rendering ----------------

def _shrink_matrix(m: List[List[bool]], step: int) -> List[List[bool]]:
    """Downsample the QR matrix by an integer step using OR pooling (preserve dark modules)."""
    if step <= 1:
        return m
    out: List[List[bool]] = []
    rows, cols = len(m), len(m[0])
    r = 0
    while r < rows:
        row: List[bool] = []
        c = 0
        while c < cols:
            blk = False
            for rr in range(r, min(r + step, rows)):
                for cc in range(c, min(c + step, cols)):
                    if m[rr][cc]:
                        blk = True
                        break
                if blk:
                    break
            row.append(blk)
            c += step
        out.append(row)
        r += step
    return out

def _make_qr_ascii(data: str, *, border: int = 0, compact: bool = True, max_cols: int = 44) -> Optional[str]:
    """
    Build a terminal-friendly QR string.
      - compact=True uses half blocks (▀▄█): ~2x width & ~2x height reduction (≈4x area).
      - max_cols applies only to compact mode; we downsample by an integer factor (1–3).
    """
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except Exception:
        return None

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=1,
        border=max(0, int(border or 0)),
    )
    qr.add_data(data)
    qr.make(fit=True)
    m = qr.get_matrix()  # type: ignore[assignment]
    width = len(m[0])

    # If compact and the QR would exceed max_cols, shrink by integer factor (preserve scan by OR pooling).
    if compact and max_cols and width > max_cols:
        step = min(max(1, ceil(width / max_cols)), 3)  # cap shrink to 3 for reliability
        if step > 1:
            m = _shrink_matrix(m, step)
            width = len(m[0])

    if compact:
        # Combine two rows into one character row via half blocks
        lines = []
        for r in range(0, len(m), 2):
            top = m[r]
            bot = m[r + 1] if r + 1 < len(m) else [False] * len(top)
            row_chars = []
            for t, b in zip(top, bot):
                if t and b:
                    ch = "█"
                elif t and not b:
                    ch = "▀"
                elif not t and b:
                    ch = "▄"
                else:
                    ch = " "
                row_chars.append(ch)
            lines.append("".join(row_chars))
        return "\n".join(lines)

    # Legacy wide blocks
    full, empty = "██", "  "
    return "\n".join("".join(full if cell else empty for cell in row) for row in m)

# ---------------- Autostart entry ----------------

def autostart(dl: Any = None, logger: Optional[logging.Logger] = None) -> Optional[str]:
    """
    Read ONLY from backend/config/webterm_config.json.
    Start web terminal if enabled+autostart; print a compact QR + a clickable hyperlink.
    """
    log = logger or logging.getLogger("webterm")

    file_cfg = _load_cfg_from_file()
    cfg = _merge(DEFAULT_CFG, file_cfg or {})

    if not cfg.get("enabled", True) or not cfg.get("autostart", True):
        return None

    url = ensure_running(cfg, dl=dl, logger=log)

    # --- Output banner (compact QR + hyperlink) ---
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich.align import Align
        from rich.columns import Columns
        from rich.box import ROUNDED

        console = Console()

        if url:
            qr_cfg = cfg.get("qr", {}) or {}
            border  = int(qr_cfg.get("border", 0))
            compact = bool(qr_cfg.get("compact", True))
            max_cols = int(qr_cfg.get("max_cols", 44))
            color   = str(qr_cfg.get("color", "green"))
            label   = str(qr_cfg.get("link_label", "Open Web Terminal"))

            qr_txt = _make_qr_ascii(url, border=border, compact=compact, max_cols=max_cols)

            # Clickable hyperlink (OSC-8). Most modern terminals (Windows Terminal/VSCode/iTerm) support it.
            link = Text.assemble((label + " → ", "bold"), (url, f"bold underline link {url}"))
            link.justify = "center"

            if qr_txt:
                body = Align.center(Text(qr_txt, style=color))
                console.print(
                    Panel(
                        Align.center(Columns([body, Align.center(link)], expand=True, equal=True, align="center")),
                        title="Web Terminal (QR)",
                        border_style=color,
                        box=ROUNDED,
                        padding=(1, 2),
                    )
                )
            else:
                # fallback: no qrcode module installed
                console.print(
                    Panel.fit(
                        Align.center(link),
                        title="Sonic",
                        border_style="cyan",
                        box=ROUNDED,
                        padding=(1, 2),
                    )
                )
        else:
            console.print(
                Panel.fit(
                    Text("🌐 Web Terminal: starting…", style="bold yellow"),
                    title="Sonic",
                    border_style="yellow",
                    box=ROUNDED,
                    padding=(1, 2),
                )
            )
    except Exception:
        print(f"[Sonic] Web Terminal: {url or 'starting…'}")

    return url
