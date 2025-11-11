# preferred multi-channel dispatcher with graceful fallback
try:
    from .xcom_core import dispatch_notifications  # the multi-channel aggregator
except Exception:  # pragma: no cover - compatibility shim
    try:
        from .dispatcher import dispatch_notifications
    except Exception:  # pragma: no cover - compatibility shim
        from .dispatch import dispatch_voice_if_needed as dispatch_notifications  # type: ignore

# Legacy symbol — keep import from callers from breaking, but don’t load old module.
XComCore = None  # type: ignore

__all__ = ["dispatch_notifications", "XComCore"]
