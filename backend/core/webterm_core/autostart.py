from __future__ import annotations

import json
import logging
import re
import time
from math import ceil
from pathlib import Path
from typing import Any, Dict, Optional, List

from .manager import ensure_running

CONFIG_PATH = Path("backend/config/webterm_config.json")
STATE_PATH  = Path("reports/webterm_state.json")
CF_LOG      = Path("reports/cloudflared.log")

DEFAULT_CFG: Dict[str, Any] = {
    "enabled": True,
    "autostart": True,
    "provider": "cloudflare",     # "cloudflare" | "tailscale" | "none"
    "port": 7681,
    "command": r"C:\\sonic7\\.venv\\Scripts\\python.exe C:\\sonic7\\launch_pad.py ; pwsh",
    "auth": {},                   # no Basic Auth by default
    "cloudflare": { "mode": "quick", "hostname": None, "tunnel_name": None },
    "qr": {
        "enabled": True,
        "border": 0,
        "compact": True,
        "max_cols": 44,
        "color": "green",
        "link_label": "Open Web Terminal"
    }
}

# STRICT quick-tunnel URL pattern only
_TRYCF_URL_RE = re.compile(
    r"https?://[a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.trycloudflare\.com(?:/[^\s]*)?",
    re.IGNORECASE,
)


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = v if not v else _merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_json(path: Path) -> Optional[Dict]:
    try:
        if not path.exists(): return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_cfg() -> Dict[str, Any]:
    cfg = _read_json(CONFIG_PATH)
    if cfg is None:
        _write_json(CONFIG_PATH, DEFAULT_CFG)
        cfg = dict(DEFAULT_CFG)
    return cfg


def _url_from_state() -> Optional[str]:
    st = _read_json(STATE_PATH) or {}
    u = st.get("url")
    return str(u) if u else None


def _url_from_cf_log() -> Optional[str]:
    if not CF_LOG.exists(): return None
    try:
        txt = CF_LOG.read_text(encoding="utf-8", errors="ignore")
        m = _TRYCF_URL_RE.search(txt)
        return m.group(0) if m else None
    except Exception:
        return None


def _poll_url(initial: Optional[str], provider: str, mode: str, wait_s: float = 8.0) -> Optional[str]:
    if initial: return initial
    deadline = time.time() + max(0.0, wait_s)
    while time.time() < deadline:
        u = _url_from_state()
        if u: return u
        if provider == "cloudflare" and mode == "quick":
            u = _url_from_cf_log()
            if u: return u
        time.sleep(0.3)
    return None


# ---- QR rendering (compact) ----
def _shrink_matrix(m: List[List[bool]], step: int) -> List[List[bool]]:
    if step <= 1: return m
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
                    if m[rr][cc]: blk = True; break
                if blk: break
            row.append(blk)
            c += step
        out.append(row); r += step
    return out


def _make_qr_ascii(data: str, *, border: int = 0, compact: bool = True, max_cols: int = 44) -> Optional[str]:
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_M
    except Exception:
        return None
    qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M, box_size=1, border=max(0, int(border or 0)))
    qr.add_data(data); qr.make(fit=True)
    m = qr.get_matrix()
    width = len(m[0])
    if compact and max_cols and width > max_cols:
        step = min(max(1, ceil(width / max_cols)), 3)
        if step > 1: m = _shrink_matrix(m, step)
    if compact:
        lines = []
        for r in range(0, len(m), 2):
            top = m[r]; bot = m[r+1] if r+1 < len(m) else [False]*len(top)
            row = []
            for t,b in zip(top, bot):
                row.append("█" if t and b else "▀" if t else "▄" if b else " ")
            lines.append("".join(row))
        return "\n".join(lines)
    full, empty = "██", "  "
    return "\n".join("".join(full if cell else empty for cell in row) for row in m)


def autostart(dl: Any = None, logger: Optional[logging.Logger] = None) -> Optional[str]:
    log = logger or logging.getLogger("webterm")

    file_cfg = _load_cfg()
    cfg = _merge(DEFAULT_CFG, file_cfg or {})
    if not cfg.get("enabled", True) or not cfg.get("autostart", True):
        return None

    provider = str(cfg.get("provider", "cloudflare")).lower().strip()
    mode     = str((cfg.get("cloudflare") or {}).get("mode", "named")).lower().strip()

    url0 = ensure_running(cfg, dl=dl, logger=log)
    url  = _poll_url(url0, provider, mode, wait_s=8.0)

    # -------- Output: compact QR + clickable hyperlink to REAL URL --------
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        from rich.align import Align
        from rich.columns import Columns
        from rich.box import ROUNDED

        console = Console()
        if url:
            qr_cfg   = cfg.get("qr", {}) or {}
            border   = int(qr_cfg.get("border", 0))
            compact  = bool(qr_cfg.get("compact", True))
            max_cols = int(qr_cfg.get("max_cols", 44))
            color    = str(qr_cfg.get("color", "green"))
            label    = str(qr_cfg.get("link_label", "Open Web Terminal"))

            qr_txt = _make_qr_ascii(url, border=border, compact=compact, max_cols=max_cols)
            link   = Text.assemble((label + " → ", "bold"), (url, f"bold underline link {url}"))
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
                console.print(
                    Panel.fit(Align.center(link), title="Sonic", border_style="cyan", box=ROUNDED, padding=(1, 2))
                )
        else:
            console.print(
                Panel.fit(Text("🌐 Web Terminal: starting…", style="bold yellow"),
                          title="Sonic", border_style="yellow", box=ROUNDED, padding=(1, 2))
            )
    except Exception:
        print(f"[Sonic] Web Terminal: {url or 'starting…'}")

    return url
