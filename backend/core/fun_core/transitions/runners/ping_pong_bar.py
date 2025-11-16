# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from ..base import TransitionContext
from .. import util as U, themes as T

class Runner:
    name = "ping_pong_bar"

    def run(self, ctx: TransitionContext) -> None:
        U.enable_ansi_on_windows()
        theme = ctx.theme or T.DEFAULT_THEME
        w, h = (ctx.width or 0), (ctx.height or 0)
        if w <= 0 or h <= 0:
            w, h = U.console_size()

        # Single-line header: "🌀 Next Cycle  00:00 [ping pong bar]"
        title = "🌀 Next Cycle"
        bar_w = max(18, min(w - 20, 60))
        left_pad = max(2, (w - (bar_w + 14)) // 2)
        fun_line = (ctx.get_fun_line() if ctx.get_fun_line else "") or ""

        U.clear_screen()
        with U.hidden_cursor():
            for i, elapsed, remaining in U.fps_loop(ctx.duration_s, ctx.fps):
                # position bounces end-to-end
                frame = i % ((bar_w - 1) * 2)
                pos = frame if frame < (bar_w - 1) else (bar_w - 1) * 2 - frame

                # draw
                U.home()

                # build the bar
                bar = T.H_BAR_L + "".join(
                    (T.H_MARK if idx == pos else " ")
                    for idx in range(bar_w)
                ) + T.H_BAR_R
                if not ctx.emoji:
                    bar = "[" + "".join(
                        "=" if idx == pos else " " for idx in range(bar_w)
                    ) + "]"

                bar_with_pad = " " * left_pad + bar

                # single-line header: title + timer + bar
                header = (
                    f"{theme.title_color}{title}{U.RESET}"
                    f"  {theme.accent}{U.seconds_to_mmss(remaining)}{U.RESET}  "
                    f"{bar_with_pad}"
                )
                sys.stdout.write(header + "\n")

                # optional fun line on the next line
                if fun_line:
                    sys.stdout.write(
                        "\n" + " " * left_pad +
                        f"{theme.text_color}{fun_line}{U.RESET}\n"
                    )

                U.clear_down()
                sys.stdout.flush()
