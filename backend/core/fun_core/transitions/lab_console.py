# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys
from typing import Optional
from .base import TransitionContext
from .registry import list_runners, get_runner, random_runner

def _get_fun_line():
    try:
        from backend.core.fun_core import quotes, jokes
        import random
        return (quotes.random_one_liner() if hasattr(quotes,"random_one_liner") else quotes.random()) \
               if random.random() < 0.7 else \
               (jokes.random_short() if hasattr(jokes,"random_short") else jokes.random())
    except Exception:
        return "Loading good vibes…"

def _ctx_from_env() -> TransitionContext:
    return TransitionContext(
        duration_s=int(os.getenv("FUN_TRANSITIONS_DURATION_S","60")),
        fps=int(os.getenv("FUN_TRANSITIONS_FPS","12")),
        width=0, height=0,
        color=os.getenv("FUN_TRANSITIONS_COLOR","1") not in {"0","false","False","no","NO"},
        emoji=os.getenv("FUN_TRANSITIONS_EMOJI","1") not in {"0","false","False","no","NO"},
        title="Next cycle starts in",
        get_fun_line=_get_fun_line
    )

def main(selected: Optional[str] = None):
    """
    Standalone lab. If `selected` is None, show a simple menu in the console.
    Otherwise, run that runner by name.
    """
    if selected is None:
        names = list_runners()
        print("\n🧪 Transitions Lab")
        for i, n in enumerate(names, 1):
            print(f"  {i}) {n}")
        print("  r) random")
        print("  0) back\n")
        choice = input("Pick one: ").strip().lower()
        if choice in {"0","q","quit","back"}:
            return
        if choice == "r":
            runner = random_runner()
        else:
            try:
                idx = int(choice)
                runner = get_runner(names[idx-1])
            except Exception:
                print("Invalid choice.")
                return
    else:
        runner = get_runner(selected)

    ctx = _ctx_from_env()
    runner.run(ctx)
