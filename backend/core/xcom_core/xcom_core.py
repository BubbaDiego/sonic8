from __future__ import annotations

# Legacy entry point removed on purpose.
# Stop importing XComCore and call the consolidated dispatcher instead:
#     from backend.core.xcom_core import dispatch_notifications

raise ImportError(
    "XComCore has been removed. Use 'from backend.core.xcom_core import dispatch_notifications' "
    "and pass result={'breach': True/False, 'summary': ...} plus channels=None to use JSON defaults."
)
