
"""Alert threshold data models."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class AlertThreshold:
    """Represents a single alert threshold record."""

    id: str
    alert_type: str
    alert_class: str
    metric_key: str
    condition: str
    low: float
    medium: float
    high: float
    enabled: bool = True
    last_modified: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    low_notify: str = ""
    medium_notify: str = ""
    high_notify: str = ""

    def to_dict(self) -> dict:
        """Return a plain dictionary representation."""
        return asdict(self)


__all__ = ["AlertThreshold"]
