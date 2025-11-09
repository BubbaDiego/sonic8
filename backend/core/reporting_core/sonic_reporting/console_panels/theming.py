from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── width / hr ────────────────────────────────────────────────────────────────
def console_width(default: int = 92) -> int:
    try:
        return max(60, min(180, int(os.environ.get("SONIC_CONSOLE_WIDTH", default))))
    except Exception:
        return default


def hr(width: Optional[int] = None, ch: str = "─") -> str:
    W = width or console_width()
    return ch * W


# ── color utils ───────────────────────────────────────────────────────────────
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
}
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _ansi(name: str, s: str) -> str:
    code = _COLOR.get(str(name or "").lower(), "")
    return f"\x1b[{code}m{s}\x1b[0m" if (_USE_COLOR and code) else s


# ── Rich integration (for true rounded boxes) ──────────────────────────────────
_RICH_ROUNDED: Dict[str, str]
try:
    from rich.box import ROUNDED as _RB  # type: ignore

    def _rb_get(obj: Any, *names: str, default: str = "") -> str:
        for name in names:
            if hasattr(obj, name):
                value = getattr(obj, name)
                if isinstance(value, str):
                    return value
        return default

    _RICH_ROUNDED = {
        "tl": _rb_get(_RB, "upper_left", "tl", "UL", default="╭"),
        "tr": _rb_get(_RB, "upper_right", "tr", "UR", default="╮"),
        "bl": _rb_get(_RB, "lower_left", "bl", "LL", default="╰"),
        "br": _rb_get(_RB, "lower_right", "br", "LR", default="╯"),
        "h": _rb_get(_RB, "horizontal", "h", default="─"),
        "v": _rb_get(_RB, "vertical", "v", default="│"),
    }
except Exception:
    _RICH_ROUNDED = {
        "tl": "╭",
        "tr": "╮",
        "bl": "╰",
        "br": "╯",
        "h": "─",
        "v": "│",
    }


def _display_len(s: str) -> int:
    return len(_ANSI_RE.sub("", s))


# ── config loader ────────────────────────────────────────────────────────────
_cfg_cache: Optional[Dict[str, Any]] = None


def _load_config() -> Dict[str, Any]:
    # default path lives next to this file
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


# ── config accessors ─────────────────────────────────────────────────────────
def get_panel_title_config(slug: str, *, default_string: str) -> Dict[str, Any]:
    cfg = _cfg()
    defaults = (cfg.get("defaults") or {}).get("title") or {}
    panels = cfg.get("panels") or {}
    panel = (panels.get(slug) or {}).get("title") or {}

    def pick(*keys: str, default: Any = None) -> Any:
        for k in keys:
            if k in panel and panel[k] not in (None, ""):
                return panel[k]
        for k in keys:
            if k in defaults and defaults[k] not in (None, ""):
                return defaults[k]
        return default

    return {
        "string": pick("string", default=default_string),
        "icon": pick("icon", default=""),
        "border_style": str(pick("border_style", default="lines")).lower(),
        "border_color": pick("border_color", default="default"),
        "text_color": pick("text_color", default="cyan"),
    }


# ── title renderers ──────────────────────────────────────────────────────────
def _center_piece(piece: str, width: int) -> Tuple[int, int]:
    fill = max(0, width - _display_len(piece))
    left = fill // 2
    right = fill - left
    return left, right


def _lines_style(text: str, *, width: int, border_color: str, text_color: str) -> List[str]:
    # e.g., ─────  Title  ─────
    shown_plain = f"  {text}  "
    left_fill, right_fill = _center_piece(shown_plain, width)
    left = "─" * left_fill
    right = "─" * right_fill
    if border_color and border_color != "default":
        left = _ansi(border_color, left)
        right = _ansi(border_color, right)
    shown = f"  {_ansi(text_color, text)}  "
    return [f"{left}{shown}{right}"]


def _rectangle_style(text: str, *, width: int, border_color: str, text_color: str) -> List[str]:
    # three lines, centered box around the title row
    text_len = _display_len(text)
    inner_width = text_len + 2  # at least one space on each side
    box_w = min(width, max(10, inner_width + 2))
    top = "┌" + "─" * (box_w - 2) + "┐"
    available = box_w - 2
    pad_total = max(0, available - text_len)
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    mid = "│" + (" " * pad_left) + _ansi(text_color, text) + (" " * pad_right) + "│"
    bot = "└" + "─" * (box_w - 2) + "┘"
    left_pad, _ = _center_piece(top, width)
    pad = " " * left_pad
    if border_color and border_color != "default":
        top = _ansi(border_color, top)
        mid = _ansi(border_color, mid)
        bot = _ansi(border_color, bot)
    return [pad + top, pad + mid, pad + bot]


def _rounded_style(text: str, *, width: int, border_color: str, text_color: str) -> List[str]:
    tl = _RICH_ROUNDED["tl"]
    tr = _RICH_ROUNDED["tr"]
    bl = _RICH_ROUNDED["bl"]
    br = _RICH_ROUNDED["br"]
    h = _RICH_ROUNDED["h"]
    v = _RICH_ROUNDED["v"]

    text_len = _display_len(text)
    inner_width = text_len + 2
    box_w = min(width, max(10, inner_width + 2))
    top = tl + (h * (box_w - 2)) + tr
    available = box_w - 2
    pad_total = max(0, available - text_len)
    pad_left = pad_total // 2
    pad_right = pad_total - pad_left
    mid = v + (" " * pad_left) + _ansi(text_color, text) + (" " * pad_right) + v
    bot = bl + (h * (box_w - 2)) + br
    left_pad, _ = _center_piece(top, width)
    pad = " " * left_pad
    if border_color and border_color != "default":
        top = _ansi(border_color, top)
        mid = _ansi(border_color, mid)
        bot = _ansi(border_color, bot)
    return [pad + top, pad + mid, pad + bot]


def _none_style(text: str, *, width: int, border_color: str, text_color: str) -> List[str]:
    # centered plain title, no rails/box
    left_pad, right_pad = _center_piece(text, width)
    return [(" " * left_pad) + _ansi(text_color, text) + (" " * right_pad)]


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
        return _none_style(text, width=W, border_color=tcfg["border_color"], text_color=tcfg["text_color"])
    return _lines_style(text, width=W, border_color=tcfg["border_color"], text_color=tcfg["text_color"])
