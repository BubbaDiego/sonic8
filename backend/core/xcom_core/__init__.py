"""
XCOM consolidated API (public surface).

Import wherever you need to notify:
    from backend.core.xcom_core import dispatch_notifications
"""

from .dispatch import dispatch_notifications

__all__ = ["dispatch_notifications"]
