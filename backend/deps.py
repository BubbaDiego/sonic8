"""Dependency helpers for FastAPI routes."""

from flask import current_app, has_app_context

from backend.data.data_locker import DataLocker
from backend.core.core_constants import MOTHER_DB_PATH


def get_app_locker() -> DataLocker:
    """Return the active :class:`DataLocker` instance for the Flask app."""
    app = current_app if has_app_context() else None
    return getattr(app, "data_locker", None) or DataLocker.get_instance()


def get_locker():
    """Dependency injection helper to provide DataLocker instance."""
    return DataLocker(str(MOTHER_DB_PATH))


__all__ = ["get_app_locker"]

