import asyncio
import logging
from typing import Callable, List

_listeners: List[Callable] = []


def register_listener(callback: Callable) -> Callable:
    """Register a callback invoked after each successful Sonic cycle."""
    _listeners.append(callback)
    return callback


def unregister_listener(callback: Callable) -> None:
    """Remove a previously registered listener."""
    try:
        _listeners.remove(callback)
    except ValueError:
        pass


async def notify_listeners() -> None:
    for cb in list(_listeners):
        try:
            result = cb()
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            logging.exception("Error in sonic monitor listener")
