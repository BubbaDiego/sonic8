# backend/core/reporting_core/__init__.py
"""
Lightweight init for reporting_core.

Avoid importing submodules here to prevent circular imports
(e.g., sonic_monitor -> reporting_core.spinner -> __init__).
Import the specific helpers where you use them, like:

    from backend.core.reporting_core.sonic_reporting import render_under_xcom_live
"""
__all__ = []
