# robust re-export so callers always get the aggregator when present
try:
    from .xcom_core import dispatch_notifications  # multi-channel aggregator
except Exception:  # pragma: no cover - compatibility shim
    try:
        from .dispatcher import dispatch_notifications
    except Exception:  # pragma: no cover - compatibility shim
        from .dispatch import dispatch_voice_if_needed as dispatch_notifications  # type: ignore

__all__ = ["dispatch_notifications"]
