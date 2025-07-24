from uuid import uuid4
from backend.models.alert_thresholds import AlertThreshold
from backend.data.dl_thresholds import DLThresholdManager
from backend.core.logging import log


class ThresholdService:
    """High level wrapper around ``DLThresholdManager``."""

    def __init__(self, db):
        self.repo = DLThresholdManager(db)

    def get_thresholds(self, alert_type: str, alert_class: str, condition: str) -> AlertThreshold:
        threshold = self.repo.get_by_type_and_class(alert_type, alert_class, condition)
        if not threshold:
            log.warning(
                f"\N{WARNING SIGN} No threshold match: {alert_type}/{alert_class}/{condition}",
                source="ThresholdService",
            )
        return threshold

    def create_threshold(self, threshold: AlertThreshold) -> bool:
        try:
            if not threshold.id:
                threshold.id = str(uuid4())
            return self.repo.insert(threshold)
        except Exception as e:  # pragma: no cover - db failures unexpected
            log.error(f"\N{CROSS MARK} Failed to create threshold: {e}", source="ThresholdService")
            return False

    def update_threshold(self, threshold_id: str, updates: dict) -> bool:
        try:
            return self.repo.update(threshold_id, updates)
        except Exception as e:  # pragma: no cover - db failures unexpected
            log.error(
                f"\N{CROSS MARK} Failed to update threshold {threshold_id}: {e}",
                source="ThresholdService",
            )
            return False

    def delete_threshold(self, threshold_id: str) -> bool:
        try:
            return self.repo.delete(threshold_id)
        except Exception as e:  # pragma: no cover - db failures unexpected
            log.error(
                f"\N{CROSS MARK} Failed to delete threshold {threshold_id}: {e}",
                source="ThresholdService",
            )
            return False

    def list_all_thresholds(self) -> list:
        try:
            return self.repo.get_all()
        except Exception as e:  # pragma: no cover - db failures unexpected
            log.error(f"\N{CROSS MARK} Failed to list thresholds: {e}", source="ThresholdService")
            return []

    def load_config(self) -> dict:
        """Return the full threshold configuration."""
        try:
            return self.repo.load_config()
        except Exception as e:  # pragma: no cover - file access unexpected
            log.error(f"Failed to load threshold config: {e}", source="ThresholdService")
            return {}

    def replace_config(self, config: dict) -> bool:
        """Replace all thresholds and cooldowns."""
        try:
            self.repo.replace_config(config)
            return True
        except Exception as e:  # pragma: no cover - unexpected
            log.error(f"Failed to replace config: {e}", source="ThresholdService")
            return False

    def set_threshold(
        self,
        alert_type: str,
        alert_class: str,
        low: float | None,
        high: float | None,
        *,
        condition: str = "ABOVE",
        metric_key: str | None = None,
    ) -> bool:
        """Create or update a simple threshold row.

        Only ``low`` and ``high`` values are modified. A new row is inserted if
        no existing threshold matches ``alert_type``, ``alert_class`` and
        ``condition``.
        """

        existing = self.repo.get_by_type_and_class(alert_type, alert_class, condition)

        try:
            low_val = float(low) if low is not None else None
        except Exception:
            low_val = None
        try:
            high_val = float(high) if high is not None else None
        except Exception:
            high_val = None

        if existing:
            updates = {}
            if low_val is not None:
                updates["low"] = low_val
            if high_val is not None:
                updates["high"] = high_val
            return self.update_threshold(existing.id, updates) if updates else True

        if metric_key is None:
            metric_key = {
                "Profit": "pnl_after_fees_usd",
                "TotalProfit": "pnl_after_fees_usd",
                "LiquidationDistance": "liquidation_distance",
                "HeatIndex": "heat_index",
                "TravelPercent": "travel_percent",
            }.get(alert_type, "value")

        threshold = AlertThreshold(
            id=str(uuid4()),
            alert_type=alert_type,
            alert_class=alert_class,
            metric_key=metric_key,
            condition=condition,
            low=low_val or 0.0,
            medium=0.0,
            high=high_val or 0.0,
        )
        return self.create_threshold(threshold)


__all__ = ["ThresholdService"]
