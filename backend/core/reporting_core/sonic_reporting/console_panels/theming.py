from __future__ import annotations
import json, os, re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# Width / rules
# ──────────────────────────────────────────────────────────────────────────────

def console_width(default: int = 92) -> int:
    try:
        return max(60, min(180, int(os.environ.get("SONIC_CONSOLE_WIDTH", default))))
    except Exception:
        return default

def hr(width: Optional[int] = None, ch: str = "─") -> str:
    W = width or console_width()
    return ch * W

# ──────────────────────────────────────────────────────────────────────────────
# ANSI color helpers
# ──────────────────────────────────────────────────────────────────────────────

_USE_COLOR = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0", "false", "no", "off"}
_COLOR = {
    "default": "",
    "cyan": "36;1",
    "yellow": "33;1",
    "blue": "34;1",
    "magenta": "35;1",
    "green": "32;1",
    "red": "31;1",
    "grey50": "90",
    "orange1": "38;5;208",
    "white": "37;1",
}

def _ansi(color_name: str, s: str) -> str:
    code = _COLOR.get(str(color_name or "").lower(), "")
    return f"\x1b[{code}m{s}\x1b[0m" if (_USE_COLOR and code) else s

# detect if string already contains ANSI escapes (so we don't double-paint)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def has_ansi(s: str) -> bool:
    return bool(_ANSI_RE.search(s))

def color_if_plain(s: str, color_name: str) -> str:
    if not color_name or color_name == "default":
        return s
    # If there is already any ANSI in the cell/line, leave it untouched.
    return s if has_ansi(s) else _ansi(color_name, s)

def paint_line(line: str, color_name: str) -> str:
    # Paint entire line regardless (used for totals/header lines).
    return _ansi(color_name, line) if color_name and color_name != "default" else line

# ──────────────────────────────────────────────────────────────────────────────
# Config loader
# ──────────────────────────────────────────────────────────────────────────────

_cfg_cache: Optional[Dict[str, Any]] = None

def _load_config() -> Dict[str, Any]:
    default_path = Path(__file__).parent / "panel_config.json"
    path = Path(os.getenv("PANEL_CONFIG_PATH", str(default_path)))
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if text.strip() else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def _cfg() -> Dict[str, Any]:
    global _cfg_cache
    if _cfg_cache is None:
        _cfg_cache = _load_config()
    return _cfg_cache

# ──────────────────────────────────────────────────────────────────────────────
# Title config + renderer
# ──────────────────────────────────────────────────────────────────────────────

def get_panel_title_config(slug: str, *, default_string: str) -> Dict[str, Any]:
    cfg = _cfg()
    defaults = (cfg.get("defaults") or {}).get("title") or {}
    panels = cfg.get("panels") or {}
    panel = (panels.get(slug) or {}).get("title") or {}

    def pick(*keys, default=None):
        for k in keys:
            if k in panel and panel[k] not in (None, ""):
                return panel[k]
        for k in keys:
            if k in defaults and defaults[k] not in (None, ""):
                return defaults[k]
        return default

    return {
        "string":       pick("string", default=default_string),
        "icon":         pick("icon", default=""),
        "border_style": str(pick("border_style", default="lines")).lower(),
        "border_color": pick("border_color", default="default"),
        "text_color":   pick("text_color", default="cyan"),
    }

def _center_piece(piece: str, width: int) -> Tuple[int, int]:
    fill = max(0, width - len(piece))
    left = fill // 2
    right = fill - left
    return left, right

def _lines_style(title_txt: str, *, width: int, border_color: str, text_color: str) -> List[str]:
    shown = f"  {title_txt}  "
    L, R = _center_piece(shown, width)
    left = "─" * L
    right = "─" * R
    if border_color and border_color != "default":
        left = _ansi(border_color, left)
        right = _ansi(border_color, right)
    return [f"{left}{_ansi(text_color, shown)}{right}"]

def _rectangle_style(title_txt: str, *, width: int, border_color: str, text_color: str) -> List[str]:
    inner = f" {title_txt} "
    box_w = min(width, max(10, len(inner) + 2))
    top = "┌" + "─" * (box_w - 2) + "┐"
    mid = "│" + inner.center(box_w - 2) + "│"
    bot = "└" + "─" * (box_w - 2) + "┘"
    L, _ = _center_piece(top, width)
    pad = " " * L
    if border_color and border_color != "default":
        top = _ansi(border_color, top); mid = _ansi(border_color, mid); bot = _ansi(border_color, bot)
    return [pad + top, pad + _ansi(text_color, mid), pad + bot]

# Rich rounded support
_RICH_ROUNDED: Optional[dict] = None
try:
    from rich.box import ROUNDED as _RB  # type: ignore
    def _rb_get(obj, *names, default=""):
        for n in names:
            if hasattr(obj, n):
                return getattr(obj, n)
        return default
    _RICH_ROUNDED = dict(
        tl=_rb_get(_RB, "upper_left", "tl", "UL", default="╭"),
        tr=_rb_get(_RB, "upper_right", "tr", "UR", default="╮"),
        bl=_rb_get(_RB, "lower_left", "bl", "LL", default="╰"),
        br=_rb_get(_RB, "lower_right", "br", "LR", default="╯"),
        h=_rb_get(_RB, "horizontal", "h", default="─"),
        v=_rb_get(_RB, "vertical", "v", default="│"),
    )
except Exception:
    _RICH_ROUNDED = dict(tl="╭", tr="╮", bl="╰", br="╯", h="─", v="│")

def _rounded_style(title_txt: str, *, width: int, border_color: str, text_color: str) -> List[str]:
    tl = _RICH_ROUNDED["tl"]; tr = _RICH_ROUNDED["tr"]
    bl = _RICH_ROUNDED["bl"]; br = _RICH_ROUNDED["br"]
    h  = _RICH_ROUNDED["h"];  v  = _RICH_ROUNDED["v"]
    inner = f" {title_txt} "
    text_len = len(inner)
    box_w = min(width, max(10, text_len + 2))
    top = tl + (h * (box_w - 2)) + tr
    avail = box_w - 2
    pad_total = max(0, avail - len(inner))
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    mid = v + (" " * pad_left) + _ansi(text_color, inner) + (" " * pad_right) + v
    bot = bl + (h * (box_w - 2)) + br
    L, _ = _center_piece(top, width)
    pad = " " * L
    if border_color and border_color != "default":
        top = _ansi(border_color, top); mid = _ansi(border_color, mid); bot = _ansi(border_color, bot)
    return [pad + top, pad + mid, pad + bot]

def title_lines(slug: str, default_string: str, *, width: Optional[int] = None) -> List[str]:
    W = width or console_width()
    tcfg = get_panel_title_config(slug, default_string=default_string)
    text = tcfg["string"] or default_string
    if tcfg["icon"]:
        text = f"{tcfg['icon']} {text} {tcfg['icon']}"

    style = tcfg["border_style"]
    if style == "rectangle":
        return _rectangle_style(text, width=W, border_color=tcfg["border_color"], text_color=tcfg["text_color"])
    if style == "rounded":
        return _rounded_style(text, width=W, border_color=tcfg["border_color"], text_color=tcfg["text_color"])
    if style == "none":
        return _none_style(text, width=W, border_color=tcfg["border_color"])
    return _lines_style(text, width=W, border_color=tcfg["border_color"], text_color=tcfg["text_color"])

def _none_style(title_txt: str, *, width: int, border_color: str) -> List[str]:
    shown = title_txt
    L, R = _center_piece(shown, width)
    return [(" " * L) + shown + (" " * R)]

# ──────────────────────────────────────────────────────────────────────────────
# Body config + helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_panel_body_config(slug: str) -> Dict[str, str]:
    """
    Returns:
      {
        "column_header_text_color": "...",
        "body_text_color": "...",
        "totals_row_color": "..."
      }
    All keys optional; defaults fall back to `defaults.body` or "default".
    """
    cfg = _cfg()
    defaults = (cfg.get("defaults") or {}).get("body") or {}
    panels = cfg.get("panels") or {}
    panel_body = (panels.get(slug) or {}).get("body") or {}

    def pick(key: str, default: str = "default") -> str:
        if key in panel_body and panel_body[key] not in (None, ""):
            return str(panel_body[key])
        if key in defaults and defaults[key] not in (None, ""):
            return str(defaults[key])
        return default

    return {
        "column_header_text_color": pick("column_header_text_color"),
        "body_text_color": pick("body_text_color"),
        "totals_row_color": pick("totals_row_color"),
    }


def want_outer_hr(slug: str, *, default_string: str) -> bool:
    """
    True => caller should print hr() above/below the title.
    False => title is a self-contained block (rounded/rectangle), so no outer hr.
    """
    tcfg = get_panel_title_config(slug, default_string=default_string)
    style = (tcfg.get("border_style") or "lines").lower()
    return style not in {"rounded", "rectangle"}
