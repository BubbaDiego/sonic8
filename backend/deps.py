"""Dependency helpers for FastAPI routes."""

from flask import current_app, has_app_context
from backend.data.data_locker import DataLocker


def get_locker() -> DataLocker:
    """Return the active :class:`DataLocker` instance."""
    app = current_app if has_app_context() else None
    return getattr(app, "data_locker", None) or DataLocker.get_instance()

__all__ = ["get_locker"]
