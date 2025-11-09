# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, time
from typing import List
from ..base import TransitionContext
from .. import util as U, themes as T

class Runner:
    name = "bouncing_ball"

    def run(self, ctx: TransitionContext) -> None:
        U.enable_ansi_on_windows()
        theme = ctx.theme or T.DEFAULT_THEME
        width, height = (ctx.width or 0), (ctx.height or 0)
        if width <= 0 or height <= 0:
            width, height = U.console_size()

        # Box geometry
        bw = max(20, min(width - 6, 60))
        bh = max(8,  min(height - 8, 18))
        ox = (width - bw)//2
        oy = (height - bh)//2

        # Symbols
        ball = T.BALL if ctx.emoji and U.supports_emoji() else T.BALL_ASC
        TL,TR,BL,BR,H,V = (T.BOX_TL,T.BOX_TR,T.BOX_BL,T.BOX_BR,T.BOX_H,T.BOX_V)
        if not ctx.emoji:
            TL,TR,BL,BR,H,V = (T.BOX_ASC_TL,T.BOX_ASC_TR,T.BOX_ASC_BL,T.BOX_ASC_BR,T.BOX_ASC_H,T.BOX_ASC_V)

        # Ball state
        x, y = 2, 2
        vx, vy = 1, 1

        title = (ctx.title or "Between cycles") + " — Bouncing Ball"
        fun_line = (ctx.get_fun_line() if ctx.get_fun_line else "") or ""

        U.clear_screen()
        with U.hidden_cursor():
            for i, elapsed, remaining in U.fps_loop(ctx.duration_s, ctx.fps):
                # bounce
                if x <= 1 or x >= bw-2: vx *= -1
                if y <= 1 or y >= bh-2: vy *= -1
                x += vx; y += vy

                # draw
                U.home()
                header = f"{theme.title_color}{title}{U.RESET}   {theme.accent}{U.seconds_to_mmss(remaining)}{U.RESET}"
                sys.stdout.write(header + "\n")

                # box top
                sys.stdout.write(" " * ox + TL + H*(bw-2) + TR + "\n")
                # box rows
                for r in range(bh-2):
                    row = " " * ox + V
                    for c in range(bw-2):
                        row += ball if (c==x and r==y) else " "
                    row += V
                    sys.stdout.write(row + "\n")
                # box bottom
                sys.stdout.write(" " * ox + BL + H*(bw-2) + BR + "\n")

                if fun_line:
                    fl = f"{theme.text_color}{fun_line}{U.RESET}"
                    sys.stdout.write("\n" + U.pad(fl, width) + "\n")

                U.clear_down()
                sys.stdout.flush()
