from __future__ import annotations

from typing import Any, Mapping, Sequence

# Route all legacy uses of XComCore -> consolidated dispatcher
from backend.core.xcom_core.dispatcher import (
    dispatch_notifications as _dispatch_notifications,
)

def dispatch_notifications(
    monitor_name: str,
    result: Mapping[str, Any] | None = None,
    channels: Mapping[str, Any] | Sequence[str] | str | None = None,
    context: Mapping[str, Any] | None = None,
    db_path: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Compatibility wrapper that accepts the legacy positional signature."""

    if "monitor_name" in kwargs and monitor_name is None:
        monitor_name = kwargs.pop("monitor_name")  # type: ignore[assignment]
    if "result" in kwargs and result is None:
        result = kwargs.pop("result")
    if "channels" in kwargs and channels is None:
        channels = kwargs.pop("channels")
    if "context" in kwargs and context is None:
        context = kwargs.pop("context")
    if "db_path" in kwargs and db_path is None:
        db_path = kwargs.pop("db_path")

    return _dispatch_notifications(
        monitor_name=monitor_name,
        result=result,
        channels=channels,
        context=context,
        db_path=db_path,
    )


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

    @staticmethod
    def get_latest_xcom_monitor_entry() -> dict | None:
        """
        Return the most recent XCOM monitor ledger entry as a dict (or None if not found).

        This is intentionally defensive and tries several backends so it stays
        compatible with different versions of the data layer.
        """
        # 1) Try a helper in the ledger module (various possible names)
        try:
            from backend.data.dl_monitor_ledger import (
                get_latest_xcom_monitor_entry as _impl,
            )  # type: ignore

            return _impl()
        except Exception:
            pass
        try:
            from backend.data.dl_monitor_ledger import (
                get_latest_monitor_entry as _impl,
            )  # type: ignore

            return _impl()
        except Exception:
            pass
        try:
            from backend.data.dl_monitor_ledger import (
                load_latest_entry as _impl,
            )  # type: ignore

            return _impl()
        except Exception:
            pass
        try:
            from backend.data.dl_monitor_ledger import MonitorLedger  # type: ignore

            try:
                # prefer explicit XCOM channel if supported
                return MonitorLedger(channel="xcom").latest()
            except TypeError:
                # older signature without channel
                return MonitorLedger().latest()
        except Exception:
            pass

        # 2) Fallback: DataLocker with a well-known key
        try:
            from backend.data.data_locker import DataLocker  # type: ignore

            # common keys you’ve used elsewhere — try in order
            for key in ("xcom_monitor", "monitor_ledger", "xcom"):
                try:
                    dl = DataLocker(key)
                    latest = getattr(dl, "latest", None)
                    if callable(latest):
                        return latest()
                except Exception:
                    continue
        except Exception:
            pass

        return None


def get_latest_xcom_monitor_entry() -> dict | None:
    """
    Backward-compatible free function so existing imports in routes keep working:
    from backend.core.xcom_core.xcom_core import get_latest_xcom_monitor_entry
    """

    return XComCore.get_latest_xcom_monitor_entry()
