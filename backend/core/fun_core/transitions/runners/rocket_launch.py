# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, time
from ..base import TransitionContext
from .. import util as U, themes as T

class Runner:
    name = "rocket_launch"

    def run(self, ctx: TransitionContext) -> None:
        U.enable_ansi_on_windows()
        theme = ctx.theme or T.DEFAULT_THEME
        w, h = (ctx.width or 0), (ctx.height or 0)
        if w <= 0 or h <= 0: w, h = U.console_size()

        title = (ctx.title or "Between cycles") + " — Rocket Launch"
        rocket = T.ROCKET
        rocket_h = len(rocket)
        col = max(2, (w//2) - len(rocket[0])//2)

        half = max(1, ctx.duration_s // 2)
        U.clear_screen()

        with U.hidden_cursor():
            start = time.perf_counter()

            # Countdown phase
            while True:
                now = time.perf_counter()
                elapsed = now - start
                if elapsed >= half: break
                remaining_total = ctx.duration_s - elapsed
                remaining_half  = int(half - elapsed)

                U.home()
                sys.stdout.write(f"{theme.title_color}{title}{U.RESET}   {theme.accent}{U.seconds_to_mmss(remaining_total)}{U.RESET}\n\n")
                line = f"T-minus {remaining_half:02d}s"
                sys.stdout.write((" " * col) + theme.accent + line + U.RESET + "\n")
                U.clear_down(); sys.stdout.flush()
                time.sleep(0.2)

            # Launch phase (rocket rises; slight acceleration)
            t0 = time.perf_counter()
            y = h - rocket_h - 2
            vy = 1.0
            while True:
                now = time.perf_counter()
                elapsed = now - start
                if elapsed >= ctx.duration_s: break
                remaining_total = ctx.duration_s - elapsed

                U.home()
                sys.stdout.write(f"{theme.title_color}{title}{U.RESET}   {theme.accent}{U.seconds_to_mmss(remaining_total)}{U.RESET}\n")
                # draw empty lines until rocket top
                top_y = max(2, int(y))
                sys.stdout.write("\n" * top_y)
                for row in rocket:
                    sys.stdout.write((" " * col) + theme.text_color + row + U.RESET + "\n")

                # thruster flicker
                if ctx.emoji and U.supports_emoji():
                    sys.stdout.write((" " * col) + "  " + "✨" * 2 + "\n")
                else:
                    sys.stdout.write((" " * col) + "  " + "**" + "\n")

                U.clear_down(); sys.stdout.flush()
                y -= vy
                vy *= 1.08  # accelerate
                time.sleep(0.08)
