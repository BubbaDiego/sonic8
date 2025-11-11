# preferred
from .xcom_core import dispatch_notifications  # the multi-channel aggregator

# Legacy symbol — keep import from callers from breaking, but don’t load old module.
XComCore = None  # type: ignore

__all__ = ["dispatch_notifications", "XComCore"]
