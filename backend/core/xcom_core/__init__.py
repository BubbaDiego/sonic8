"""Thin wrapper: export the consolidated XCOM dispatcher from dispatcher.py."""

from .dispatch import dispatch_voice_if_needed as dispatch_notifications  # re-export

# Legacy symbol — keep import from callers from breaking, but don’t load old module.
XComCore = None  # type: ignore

__all__ = ["dispatch_notifications", "XComCore"]
