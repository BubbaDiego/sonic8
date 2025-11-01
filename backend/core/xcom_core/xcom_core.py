from __future__ import annotations

from typing import Any, Mapping, Sequence

# Route all legacy uses of XComCore -> consolidated dispatcher
from backend.core.xcom_core.dispatch import dispatch_notifications


class XComCore:
    """
    Compatibility adapter.
    Keeps legacy import path alive but forwards to dispatch_notifications().
    There is NO old behavior here — this uses the same consolidated logic as monitors.
    """

    def __init__(self, system: Any | None = None) -> None:
        self.system = system

    def _infer_monitor(self, monitor_name: str | None, initiator: str | None) -> str:
        if monitor_name:
            return str(monitor_name).strip()
        cand = (initiator or "").lower()
        for k in ("liquid", "profit", "market", "price"):
            if k in cand:
                return k
        # Safe fallback — you can adjust per call site later
        return "liquid"

    def send_notification(
        self,
        *,
        level: str = "LOW",
        subject: str = "",
        body: str = "",
        initiator: str | None = None,
        mode: Mapping[str, Any] | Sequence[str] | str | None = None,
        monitor_name: str | None = None,
        context: Mapping[str, Any] | None = None,
        dl: Any | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Legacy signature:
            level, subject, body, initiator, mode=..., monitor_name=?, context=?, dl=?, **kwargs
        Forwarded to:
            dispatch_notifications(monitor_name, result={'breach': ...}, channels=mode, context=...)
        """
        breach = str(level).upper() in {"HIGH", "CRITICAL", "URGENT", "ALERT"}
        mon = self._infer_monitor(monitor_name or kwargs.get("monitor"), initiator)

        ctx = dict(context or {})
        ctx.setdefault("subject", subject or f"[{mon}] alert")
        ctx.setdefault("body", body or "")

        return dispatch_notifications(
            monitor_name=mon,
            result={"breach": breach, "summary": ctx["body"] or ctx["subject"]},
            channels=mode,
            context=ctx,
            db_path=None,
        )
