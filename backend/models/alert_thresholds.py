"""Alert threshold data models."""

from datetime import datetime, timezone


class AlertThreshold:
    """Represents a single alert threshold record."""

    def __init__(
        self,
        id: str,
        alert_type: str,
        alert_class: str,
        metric_key: str,
        condition: str,
        low: float,
        medium: float,
        high: float,
        enabled: bool = True,
        last_modified: str | None = None,
        low_notify: str = "",
        medium_notify: str = "",
        high_notify: str = "",
    ) -> None:
        self.id = id
        self.alert_type = alert_type
        self.alert_class = alert_class
        self.metric_key = metric_key
        self.condition = condition
        self.low = low
        self.medium = medium
        self.high = high
        self.enabled = enabled
        self.last_modified = (
            last_modified or datetime.now(timezone.utc).isoformat()
        )
        self.low_notify = low_notify
        self.medium_notify = medium_notify
        self.high_notify = high_notify

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "alert_class": self.alert_class,
            "metric_key": self.metric_key,
            "condition": self.condition,
            "low": self.low,
            "medium": self.medium,
            "high": self.high,
            "enabled": self.enabled,
            "last_modified": self.last_modified,
            "low_notify": self.low_notify,
            "medium_notify": self.medium_notify,
            "high_notify": self.high_notify,
        }


__all__ = ["AlertThreshold"]
