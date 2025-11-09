# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from ..base import TransitionContext
from .. import util as U, themes as T

class Runner:
    name = "rotating_circle"

    def run(self, ctx: TransitionContext) -> None:
        U.enable_ansi_on_windows()
        theme = ctx.theme or T.DEFAULT_THEME
        w, h = (ctx.width or 0), (ctx.height or 0)
        if w <= 0 or h <= 0: w, h = U.console_size()

        title = (ctx.title or "Between cycles") + " — Rotating Circle"
        frames = T.SPIN_QUARTERS if (ctx.emoji and U.supports_emoji()) else T.SPIN_ASC

        U.clear_screen()
        with U.hidden_cursor():
            for i, _, remaining in U.fps_loop(ctx.duration_s, ctx.fps):
                spinner = frames[i % len(frames)]
                U.home()
                sys.stdout.write(f"{theme.title_color}{title}{U.RESET}   {theme.accent}{U.seconds_to_mmss(remaining)}{U.RESET}\n\n")
                # center-ish
                offset = " " * max(2, (w//2) - 2)
                sys.stdout.write(offset + theme.accent + spinner + U.RESET + "\n")
                U.clear_down(); sys.stdout.flush()
