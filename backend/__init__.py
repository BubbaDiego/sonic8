"""Backend package."""

from importlib import import_module
from typing import Any

__all__ = ["core"]

def __getattr__(name: str) -> Any:  # pragma: no cover - import hook
    if name == "core":
        module = import_module("backend.core")
        globals()[name] = module
        return module
    raise AttributeError(name)
