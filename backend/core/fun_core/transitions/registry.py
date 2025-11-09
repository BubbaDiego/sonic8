# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Callable, Dict, List, Optional
from .base import TransitionContext

# lazy import factories
def _ball():    from .runners.bouncing_ball   import Runner; return Runner()
def _pong():    from .runners.ping_pong_bar   import Runner; return Runner()
def _circle():  from .runners.rotating_circle import Runner; return Runner()
def _rocket():  from .runners.rocket_launch   import Runner; return Runner()
def _fortune(): from .runners.fortune_timer   import Runner; return Runner()

REGISTRY: Dict[str, Callable[[], object]] = {
    "bouncing_ball": _ball,
    "ping_pong_bar": _pong,
    "rotating_circle": _circle,
    "rocket_launch": _rocket,
    "fortune_timer": _fortune,
}

def list_runners() -> List[str]:
    return list(REGISTRY.keys())

def get_runner(name: str):
    fac = REGISTRY.get(name)
    if not fac:
        raise KeyError(f"unknown runner: {name}")
    return fac()

def random_runner(exclude: Optional[set]=None):
    import random
    names = list(REGISTRY.keys())
    if exclude:
        names = [n for n in names if n not in exclude]
    return get_runner(random.choice(names))
