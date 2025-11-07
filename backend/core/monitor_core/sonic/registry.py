# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Tuple

# Services
from .services.prices_service import sync_prices_service
from .services.positions_service import sync_positions_service
from .services.raydium_service import sync_raydium_service

# Monitor runners
from .monitors.liquid_runner import run_liquid_monitors
from .monitors.profit_runner import run_profit_monitors
from .monitors.market_runner import run_market_monitors

Service = Callable[[Any], Dict[str, Any]]
Runner = Callable[[Any], Dict[str, Any]]

DEFAULT_SERVICES: List[Tuple[str, Service]] = [
    ("prices", sync_prices_service),
    ("positions", sync_positions_service),
    ("raydium", sync_raydium_service),
]

DEFAULT_MONITORS: List[Tuple[str, Runner]] = [
    ("liquid", run_liquid_monitors),
    ("profit", run_profit_monitors),
    ("market", run_market_monitors),
]

def _enabled(names: Iterable[str], default: List[Tuple[str, Any]]) -> List[Tuple[str, Any]]:
    name_set = {n.strip().lower() for n in names}
    out = []
    for n, fn in default:
        if not name_set or n in name_set:
            out.append((n, fn))
    return out

def get_enabled_services(cfg: Dict[str, Any]) -> List[Tuple[str, Service]]:
    names = cfg.get("services.enabled", []) or cfg.get("services", []) or []
    return _enabled(names, DEFAULT_SERVICES)

def get_enabled_monitors(cfg: Dict[str, Any]) -> List[Tuple[str, Runner]]:
    names = cfg.get("monitors.enabled", []) or cfg.get("monitors", []) or []
    return _enabled(names, DEFAULT_MONITORS)
