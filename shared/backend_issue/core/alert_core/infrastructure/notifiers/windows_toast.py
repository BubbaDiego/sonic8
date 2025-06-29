from __future__ import annotations

try:
    from win10toast import ToastNotifier
except Exception:  # pragma: no cover - optional dependency
    ToastNotifier = None

from .base import BaseNotifier


class WindowsToastNotifier(BaseNotifier):
    """Display a Windows toast notification if possible."""

    def send(self, alert) -> bool:
        if ToastNotifier is None:
            print("ToastNotifier unavailable")
            return False
        toaster = ToastNotifier()
        try:
            toaster.show_toast("Alert", alert.description, threaded=True)
            return True
        except Exception:
            return False
