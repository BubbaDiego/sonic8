"""Alert threshold data models."""

from datetime import datetime, timezone

try:
    from pydantic import BaseModel, Field
    if not hasattr(BaseModel, "__fields__"):
        raise ImportError("stub")
except Exception:  # pragma: no cover - optional dependency or stub detected
    class BaseModel:
        """Fallback used when Pydantic isn't available."""

        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

        def model_dump(self) -> dict:  # type: ignore
            return self.__dict__

        # pydantic v1 compatibility
        def dict(self) -> dict:  # type: ignore[override]
            return self.__dict__

    def Field(default=None, **_):  # type: ignore
        return default


class AlertThreshold(BaseModel):
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
    last_modified: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    low_notify: str = ""
    medium_notify: str = ""
    high_notify: str = ""

    def to_dict(self) -> dict:
        try:
            return self.model_dump()
        except AttributeError:  # pragma: no cover - stub fallback
            return self.__dict__

    class Config:
        orm_mode = True


__all__ = ["AlertThreshold"]
