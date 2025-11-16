# -*- coding: utf-8 -*-
"""
Shared DataLocker access helpers for console_panels.

Both monitor_panel and positions_panel import this as::

    from backend.core.reporting_core.sonic_reporting.console_panels import data_access

and then call::

    dl = data_access.dl_or_context(context)

This module keeps all that logic in one place so the panels stay thin and
don't reimplement the same DL resolution code.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)

try:
    # Sonic8 DataLocker lives here
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:  # pragma: no cover
    DataLocker = None  # type: ignore


def _dl_from_context(ctx: Any) -> Optional[Any]:
    """
    Try to extract a DataLocker instance from a variety of context shapes:

    - dict with key 'dl'
    - object with attribute .dl
    - direct DataLocker instance
    """
    if ctx is None:
        return None

    # Direct DataLocker
    if DataLocker is not None and isinstance(ctx, DataLocker):
        return ctx

    # Dict-style context
    if isinstance(ctx, dict):
        dl = ctx.get("dl")
        if DataLocker is not None and isinstance(dl, DataLocker):
            return dl
        if dl is not None:
            return dl

    # Object attribute
    dl_attr = getattr(ctx, "dl", None)
    if dl_attr is not None:
        return dl_attr

    return None


def _global_dlocker() -> Optional[Any]:
    """
    Fallback global DataLocker accessor.

    If DataLocker.get_instance() exists, use that.
    Otherwise, try to construct a new DataLocker() with default config.
    """
    if DataLocker is None:
        return None

    try:
        if hasattr(DataLocker, "get_instance"):
            return DataLocker.get_instance()  # type: ignore[attr-defined]
    except Exception:
        log.exception("data_access: DataLocker.get_instance() failed")

    try:
        return DataLocker()
    except Exception:
        log.exception("data_access: failed to construct DataLocker()")
        return None


def dl_or_context(ctx: Any) -> Optional[Any]:
    """
    Public entrypoint used by panels.

    Returns a DataLocker derived from the context when possible, or a global
    fallback DataLocker instance, or None if all attempts fail.
    """
    dl = _dl_from_context(ctx)
    if dl is not None:
        return dl

    dl = _global_dlocker()
    if dl is None:
        log.warning("data_access: no DataLocker available in context or globally")
    return dl
