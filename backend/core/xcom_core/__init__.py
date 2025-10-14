"""Convenience helpers for the :mod:`backend.core.xcom_core` package."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log
from backend.data.data_locker import DataLocker

from .xcom_core import XComCore

__all__ = ["dispatch_notifications", "XComCore"]


def _normalize_channels(channels: Mapping[str, Any] | Sequence[str] | str | None) -> list[str]:
    """Return a normalized list of requested notification channels.

    The console and various monitor utilities pass channel selections in
    slightly different shapes (dicts, lists, comma separated strings).
    This helper collapses those inputs into a clean ``list[str]`` so the
    dispatcher can operate consistently.
    """

    if channels is None:
        return []

    if isinstance(channels, Mapping):
        return [name for name, enabled in channels.items() if enabled]

    if isinstance(channels, str):
        channels = channels.split(",")

    # Filter out falsey/empty strings and coerce to lowercase for
    # compatibility with ``send_notification`` which expects lower case
    # identifiers ("sms", "voice", "tts", ...).
    return [str(name).strip().lower() for name in channels if str(name).strip()]


def _derive_level(explicit_level: str | None, requested_channels: Iterable[str]) -> str:
    """Pick an appropriate notification level.

    ``XComCore.send_notification`` still uses the legacy level mapping where
    ``HIGH`` triggers SMS+voice, ``MEDIUM`` triggers SMS and ``LOW`` falls back
    to email.  Console callers may provide channel selections directly (e.g.
    ``{"voice": True}``) which means the provided ``level`` may be the name of
    the channel rather than ``HIGH``/``MEDIUM``/``LOW``.  This helper maps those
    cases back onto the expected severity scale.
    """

    if explicit_level:
        level = explicit_level.strip().upper()
        if level in {"LOW", "MEDIUM", "HIGH"}:
            return level

    requested = {channel.lower() for channel in requested_channels}
    if "voice" in requested:
        return "HIGH"
    if "sms" in requested:
        return "MEDIUM"
    return "LOW"


def dispatch_notifications(
    *,
    monitor_name: str,
    result: Mapping[str, Any] | None = None,
    channels: Mapping[str, Any] | Sequence[str] | str | None = None,
    context: Mapping[str, Any] | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Route a monitor notification through :class:`XComCore`.

    The LaunchPad console and monitor runtimes share this helper so that ad-hoc
    tests and real monitor alerts exercise the same dispatch logic.  The
    function is intentionally forgiving about the shapes of ``result`` and
    ``channels`` so callers can provide lightweight payloads without duplicating
    ``XComCore`` plumbing.

    Parameters
    ----------
    monitor_name:
        Name of the monitor initiating the dispatch.  Used for logging only.
    result:
        High-level outcome dictionary from the monitor.  ``level`` and
        ``message`` keys are consulted when building the XCom payload but all
        values are echoed back in the summary for debugging purposes.
    channels:
        Desired notification channels.  Accepts either a mapping of
        ``{"sms": True}``, a list/tuple of channel names or a comma separated
        string.  The values are normalised to lowercase identifiers before
        being passed to :meth:`XComCore.send_notification`.
    context:
        Additional metadata such as ``subject``, ``body``, ``recipient`` and
        ``initiator``.  Console callers often provide Twilio credentials here so
        the helper threads the dictionary through untouched.
    db_path:
        Optional override for the DataLocker database path.  Defaults to the
        canonical ``MOTHER_DB_PATH`` used by the rest of the backend.
    """

    context = dict(context or {})
    result = dict(result or {})

    requested_channels = _normalize_channels(channels)
    level = _derive_level(result.get("level") or context.get("level"), requested_channels)

    subject = context.get("subject") or f"[{monitor_name}] {level.title()} alert"
    body = context.get("body") or result.get("message") or ""
    recipient = context.get("recipient") or ""
    initiator = context.get("initiator") or monitor_name
    ignore_cooldown = bool(context.get("ignore_cooldown", False))

    # ``mode`` drives explicit channel selection.  ``send_notification`` will
    # fall back to the legacy level fan-out if none were requested.
    mode: Sequence[str] | None
    if requested_channels:
        mode = list(dict.fromkeys(requested_channels))  # Preserve order, dedupe
    else:
        mode = None

    locker = DataLocker.get_instance(str(db_path or MOTHER_DB_PATH))
    xcom = XComCore(locker.system)

    log.debug(
        "Dispatching XCom notification",
        source="dispatch_notifications",
        payload={
            "monitor": monitor_name,
            "level": level,
            "channels": mode or ["auto"],
            "has_context": bool(context),
        },
    )

    results = xcom.send_notification(
        level=level,
        subject=subject,
        body=body,
        recipient=recipient,
        initiator=initiator,
        mode=mode,
        ignore_cooldown=ignore_cooldown,
    )

    summary = {
        "monitor": monitor_name,
        "requested_channels": mode or [],
        "level": level,
        "subject": subject,
        "success": bool(results.get("success")),
        "results": results,
        "context": context,
        "result": result,
    }

    log.debug(
        "XCom dispatch completed",
        source="dispatch_notifications",
        payload={"monitor": monitor_name, "success": summary["success"]},
    )

    return summary

