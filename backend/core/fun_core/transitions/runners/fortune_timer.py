# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, random
from ..base import TransitionContext
from .. import util as U, themes as T

def _default_fun_line() -> str:
    # Try fun_core quotes/jokes
    try:
        from backend.core.fun_core import quotes, jokes
        if random.random() < 0.7:
            # expect quotes.random_one_liner() else fallback
            if hasattr(quotes, "random_one_liner"):
                return quotes.random_one_liner() or ""
            if hasattr(quotes, "random"):
                return quotes.random() or ""
        else:
            if hasattr(jokes, "random_short"):
                return jokes.random_short() or ""
            if hasattr(jokes, "random"):
                return jokes.random() or ""
    except Exception:
        pass
    return "Take a breath. Greatness loads in silence."

class Runner:
    name = "fortune_timer"

    def run(self, ctx: TransitionContext) -> None:
        U.enable_ansi_on_windows()
        theme = ctx.theme or T.DEFAULT_THEME
        w, h = (ctx.width or 0), (ctx.height or 0)
        if w <= 0 or h <= 0: w, h = U.console_size()

        title = (ctx.title or "Between cycles") + " — Fortune & Timer"
        fun_line = (ctx.get_fun_line or _default_fun_line)()
        frames = T.SPIN_QUARTERS if (ctx.emoji and U.supports_emoji()) else T.SPIN_ASC

        # Build a simple box around the line
        inner_w = min(max(20, len(fun_line)+2), max(40, w-8))
        msg = fun_line if len(fun_line) <= inner_w-2 else fun_line[:inner_w-3] + "…"

        TL,TR,BL,BR,H,V = (T.BOX_TL,T.BOX_TR,T.BOX_BL,T.BOX_BR,T.BOX_H,T.BOX_V)
        if not ctx.emoji:
            TL,TR,BL,BR,H,V = (T.BOX_ASC_TL,T.BOX_ASC_TR,T.BOX_ASC_BL,T.BOX_ASC_BR,T.BOX_ASC_H,T.BOX_ASC_V)

        U.clear_screen()
        with U.hidden_cursor():
            for i, _, remaining in U.fps_loop(ctx.duration_s, ctx.fps):
                spinner = frames[i % len(frames)]
                U.home()
                sys.stdout.write(f"{theme.title_color}{title}{U.RESET}   {theme.accent}{U.seconds_to_mmss(remaining)}{U.RESET}\n\n")
                pad_left = max(2, (w - (inner_w+2))//2)
                # box
                sys.stdout.write(" " * pad_left + TL + H*inner_w + TR + "\n")
                sys.stdout.write(" " * pad_left + V + U.pad(msg, inner_w) + V + "\n")
                sys.stdout.write(" " * pad_left + BL + H*inner_w + BR + "\n\n")
                # countdown line
                cd = f"{spinner} Next update in {U.seconds_to_mmss(remaining)}"
                sys.stdout.write(" " * max(2, (w//2 - len(cd)//2)) + theme.accent + cd + U.RESET + "\n")
                U.clear_down(); sys.stdout.flush()
