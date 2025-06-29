from __future__ import annotations

from ..stores import _DBAdapter


class BaseNotifier:
    """Base class for notifiers."""

    def __init__(self, db: _DBAdapter | None = None) -> None:
        self.db = db

    def send(self, alert) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError
