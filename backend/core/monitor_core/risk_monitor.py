from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.data.data_locker import DataLocker
from backend.core.positions_core.position_core import PositionCore
from backend.core.xcom_core.xcom_core import XComCore
from backend.core.alert_core.threshold_service import ThresholdService
from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log
from datetime import datetime, timezone


class RiskMonitor(BaseMonitor):
    """Monitor active positions for high heat index and alert when exceeded."""

    # Legacy attribute for backward compatibility
    snooze_until = None

    def __init__(self):
        super().__init__(name="risk_monitor")
        self.dl = DataLocker(MOTHER_DB_PATH)
        self.position_core = PositionCore(self.dl)
        self.xcom_core = XComCore(self.dl.system)
        self.threshold_service = ThresholdService(self.dl.db)


    def should_notify(self):
        value = self.dl.system.get_var('snooze_until')
        snooze_until = None
        if isinstance(value, str):
            try:
                snooze_until = datetime.fromisoformat(value)
            except Exception:
                snooze_until = None

        if not snooze_until:
            snooze_until = self.__class__.snooze_until

        if snooze_until and snooze_until.tzinfo is None:
            snooze_until = snooze_until.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        return not (snooze_until and now < snooze_until)

    def _update_risk_badge(self, value):
        self.dl.system.set_var("risk_badge_value", value)

    def _update_travel_badge(self, value):
        """Persist the travel percent badge value."""
        self.dl.system.set_var("travel_risk_badge_value", value)

    def _do_work(self):
        positions = self.position_core.get_active_positions()
        max_heat = 0.0
        max_travel = 0.0
        hottest = None
        most_travel = None
        for pos in positions:
            if isinstance(pos, dict):
                heat = pos.get("heat_index")
                if heat is None:
                    heat = pos.get("current_heat_index", 0)
                travel = pos.get("travel_percent", 0)
                pos_id = pos.get("id")
            else:
                heat = getattr(pos, "heat_index", None)
                if heat is None:
                    heat = getattr(pos, "current_heat_index", 0)
                travel = getattr(pos, "travel_percent", 0)
                pos_id = getattr(pos, "id", None)
            try:
                heat = float(heat)
            except Exception:
                heat = 0.0
            try:
                travel = float(travel)
            except Exception:
                travel = 0.0
            if heat > max_heat:
                max_heat = heat
                hottest = pos
            if travel < max_travel:
                max_travel = travel
                most_travel = pos

        th = self.threshold_service.get_thresholds("HeatIndex", "Position", "ABOVE")
        badge_limit = th.low if th else 50.0
        alert_limit = th.high if th else 50.0
        travel_th = self.threshold_service.get_thresholds("TravelPercent", "Position", "BELOW")
        travel_badge_limit = travel_th.low if travel_th else 50.0
        travel_alert_limit = travel_th.high if travel_th else 50.0

        badge_value = f"{max_heat:.0f}" if max_heat >= badge_limit else None
        self._update_risk_badge(badge_value)
        travel_badge_value = f"{max_travel:.0f}" if max_travel <= -travel_badge_limit else None
        self._update_travel_badge(travel_badge_value)

        alert_triggered = (max_heat >= alert_limit) or (max_travel <= -travel_alert_limit)
        notif_result = None

        log.banner("🔥 Risk Monitor Check")
        log.info(
            f"Limits ➜ badge: {badge_limit:.2f}, alert: {alert_limit:.2f}",
            source="RiskMonitor",
        )
        log.info(
            f"Travel limits ➜ badge: {travel_badge_limit:.2f}, alert: {travel_alert_limit:.2f}",
            source="RiskMonitor",
        )
        if hottest:
            hot_id = (
                hottest.get("id") if isinstance(hottest, dict) else getattr(hottest, "id", None)
            )
            log.info(
                f"Highest heat index {max_heat:.2f} on position {hot_id}",
                source="RiskMonitor",
            )
        else:
            log.info("No active positions found", source="RiskMonitor")

        if alert_triggered:
            parts = []
            if max_heat >= alert_limit:
                parts.append(f"heat index {max_heat:.2f}")
            if max_travel <= -travel_alert_limit:
                parts.append(f"travel percent {max_travel:.2f}%")
            msg = "🔥 Position " + " and ".join(parts) + " exceeds limits."
            if self.should_notify():
                notif_result = self.xcom_core.send_notification(
                    level="HIGH",
                    subject="Risk Alert",
                    body=msg,
                    initiator="RiskMonitor",
                )
                log.error(
                    "Violation detected! HIGH alert will be sent.",
                    source="RiskMonitor",
                )
                log.info(
                    "Actions dispatched: sound, SMS and voice when available",
                    source="RiskMonitor",
                )
                self._set_silenced(False)
            else:
                log.info("Risk alert suppressed by snooze", source="RiskMonitor")
                self._set_silenced(True)
        elif badge_value:
            log.info(
                "Badge updated without alert.",
                source="RiskMonitor",
            )
            self._set_silenced(False)
        else:
            log.success(
                "No violation detected. No action required.",
                source="RiskMonitor",
            )
            self._set_silenced(False)

        return {
            "alert_triggered": alert_triggered,
            "max_heat_index": max_heat,
            "max_travel_percent": max_travel,
            "notification_result": notif_result,
        }

    def _set_silenced(self, state: bool) -> None:
        """Persist whether a risk alert was suppressed."""
        try:
            self.dl.system.set_var("risk_alert_silenced", bool(state))
        except Exception:
            pass
