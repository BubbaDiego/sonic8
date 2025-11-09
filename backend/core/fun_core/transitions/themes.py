# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from . import util as U

@dataclass
class Theme:
    title_color: str = U.FG_CYAN + U.BOLD
    text_color: str  = U.FG_WHITE
    accent: str      = U.FG_YELLOW
    ok: str          = U.FG_GREEN + U.BOLD
    warn: str        = U.FG_YELLOW + U.BOLD
    err: str         = U.FG_RED + U.BOLD

DEFAULT_THEME = Theme()

# Symbols (with ASCII fallbacks)
BALL      = "•"
BALL_ASC  = "*"
H_BAR_L   = "["
H_BAR_R   = "]"
H_MARK    = "●"
H_MARK_ASC= "="

SPIN_QUARTERS = ["◐","◓","◑","◒"]
SPIN_ASC      = ["|","/","-","\\"]

# Box drawing fallbacks
BOX_TL, BOX_TR, BOX_BL, BOX_BR = "┌","┐","└","┘"
BOX_H, BOX_V = "─","│"
BOX_ASC_TL, BOX_ASC_TR, BOX_ASC_BL, BOX_ASC_BR = "+","+","+","+"
BOX_ASC_H, BOX_ASC_V = "-","|"

# Rocket art (simple)
ROCKET = [
"   ^   ",
"  /|\\  ",
" /_|_\\ ",
" |   | ",
"/_____\\"]
