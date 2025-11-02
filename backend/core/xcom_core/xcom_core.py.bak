from __future__ import annotations

from typing import Any, Mapping, Sequence

from backend.core.logging import log


def _normalize_mode(mode: Mapping[str, Any] | Sequence[str] | str | None) -> dict[str, bool]:
    """
    Accept legacy `mode` values (None | list[str] | csv | mapping) and turn into a channel map.
    Keys: voice/system/sms/tts (all present).
    """
    if mode is None:
        # means: let JSON defaults decide; we express that by returning all False here,
        # which the consolidated dispatcher will replace with cfg.channels_for(monitor_name)
        return {"voice": False, "system": False, "sms": False, "tts": False}

    if isinstance(mode, Mapping):
        out = {k.lower(): bool(v) for k, v in mode.items()}
    else:
        if isinstance(mode, str):
            items = [p.strip().lower() for p in mode.split(",") if p.strip()]
        else:
            items = [str(p).strip().lower() for p in mode if str(p).strip()]
        out = {k: (k in items) for k in ("voice", "system", "sms", "tts")}

    for k in ("voice", "system", "sms", "tts"):
        out.setdefault(k, False)
    return out


class XComCore:
    """
    Backward-compatible shim. All sends flow into the consolidated dispatcher.

    Old signature:
      send_notification(level, subject, body, initiator='system', mode=None, **kwargs)

    Mappings:
      • channels ← derived from `mode`
      • monitor_name ← kwargs.get('monitor', 'console')
      • breach ← kwargs.get('breach', True if channels['voice'] else False)
      • context.subject/body ← subject/body
    """

    def __init__(self, system=None) -> None:
        self.system = system

    def send_notification(
        self,
        level: str,
        subject: str,
        body: str,
        initiator: str = "system",
        mode: Mapping[str, Any] | Sequence[str] | str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        monitor_name = str(kwargs.get("monitor", "console"))
        channels = _normalize_mode(mode)
        breach = bool(kwargs.get("breach", channels.get("voice", False)))

        log.debug(
            "XComCore shim -> consolidated dispatch",
            payload={
                "monitor": monitor_name,
                "breach": breach,
                "channels": channels,
                "initiator": initiator,
            },
        )

        # Lazy import avoids circulars with backend.core.xcom_core.__init__
        from backend.core.xcom_core import dispatch_notifications

        summary = dispatch_notifications(
            monitor_name=monitor_name,
            result={"breach": breach, "summary": body},
            channels=channels,
            context={"subject": subject, "body": body, "initiator": initiator},
            db_path=kwargs.get("db_path"),
        )
        return summary
