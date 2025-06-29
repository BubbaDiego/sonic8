from .base import BaseNotifier
from .sms import SMSNotifier
from .windows_toast import WindowsToastNotifier
from .router import NotificationRouter


# Default router instance used by AlertOrchestrator
default_router = NotificationRouter()

__all__ = [
    "BaseNotifier",
    "SMSNotifier",
    "WindowsToastNotifier",
    "NotificationRouter",
    "default_router",
]
