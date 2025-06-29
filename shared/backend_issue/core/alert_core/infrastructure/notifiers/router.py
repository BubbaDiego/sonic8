from __future__ import annotations

from backend.models.alert import NotificationType
from .base import BaseNotifier
from .sms import SMSNotifier
from .windows_toast import WindowsToastNotifier


class NotificationRouter:
    """Select notifiers based on ``alert.notification_type``."""

    def __init__(self) -> None:
        self._routes: dict[NotificationType, list[BaseNotifier]] = {
            NotificationType.SMS: [SMSNotifier()],
            NotificationType.WINDOWS: [WindowsToastNotifier()],
        }

    def route(self, alert) -> list[BaseNotifier]:
        """Return the notifier instances for the given alert."""
        ntype = getattr(alert, "notification_type", None)
        if ntype is None:
            return []
        if isinstance(ntype, NotificationType):
            keys = [ntype]
        else:
            keys = []
            for token in str(ntype).split("|"):
                token = token.strip()
                if not token:
                    continue
                try:
                    keys.append(NotificationType(token))
                except ValueError:
                    continue
        notifiers: list[BaseNotifier] = []
        for key in keys:
            notifiers.extend(self._routes.get(key, []))
        return notifiers
