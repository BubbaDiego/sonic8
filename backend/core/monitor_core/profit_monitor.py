from backend.core.monitor_core.base_monitor import BaseMonitor
from backend.data.data_locker import DataLocker
from backend.core.positions_core.position_core import PositionCore
from backend.core.xcom_core.xcom_core import XComCore
from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.logging import log
from backend.core.alert_core.threshold_service import ThresholdService
from datetime import datetime, timezone
import json
from collections.abc import Mapping


class ProfitMonitor(BaseMonitor):
    # Legacy attribute for backward compatibility
    snooze_until = None

    DEFAULT_CONFIG = {
        "notifications": {"system": True, "voice": True, "sms": False, "tts": True},
        "enabled": True,
    }

    def __init__(self):
        super().__init__(name="profit_monitor")
        self.dl = DataLocker(MOTHER_DB_PATH)
        self.position_core = PositionCore(self.dl)
        self.xcom_core = XComCore(self.dl.system)
        self.threshold_service = ThresholdService(self.dl.db)

    def _get_config(self) -> dict:
        """Return merged profit monitor configuration."""
        try:
            cfg = self.dl.system.get_var("profit_monitor") or {}
        except Exception:
            cfg = {}

        merged = {**self.DEFAULT_CONFIG, **cfg}

        notifications = merged.get("notifications", {})
        if isinstance(notifications, str):
            try:
                notifications = json.loads(notifications)
            except Exception:
                notifications = {}
        if not isinstance(notifications, Mapping):
            notifications = {}

        def to_bool(v):
            if isinstance(v, str):
                return v.lower() in ("1", "true", "yes", "on")
            return bool(v)

        merged["notifications"] = {
            "system": to_bool(notifications.get("system", True)),
            "voice": to_bool(notifications.get("voice", True)),
            "sms": to_bool(notifications.get("sms", False)),
            "tts": to_bool(notifications.get("tts", True)),
        }

        merged["enabled"] = to_bool(merged.get("enabled", True))

        return merged

    def should_notify(self):
        value = self.dl.system.get_var("snooze_until")
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

    def _do_work(self):
        cfg = self._get_config()

        if not cfg.get("enabled", True):
            log.info("ProfitMonitor disabled; skipping cycle", source="ProfitMonitor")
            return {"status": "Disabled", "alert_triggered": False}

        positions = self.position_core.get_active_positions()

        def _field(obj, name, default=0.0):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        total_profit = sum(
            max(float(_field(pos, "pnl_after_fees_usd", 0.0)), 0.0) for pos in positions
        )
        max_profit = 0.0
        for p in positions:
            try:
                profit = float(_field(p, "pnl_after_fees_usd", 0.0))
            except Exception:
                profit = 0.0
            if profit > max_profit:
                max_profit = profit

        portfolio_th = self.threshold_service.get_thresholds(
            "TotalProfit", "Portfolio", "ABOVE"
        )
        single_th = self.threshold_service.get_thresholds("Profit", "Position", "ABOVE")

        badge_limit = single_th.low if single_th else 0.0
        portfolio_limit = portfolio_th.high if portfolio_th else 50.0
        single_limit = single_th.high if single_th else 25.0

        badge_value = f"{max_profit:.2f}" if max_profit > badge_limit else None
        self._update_profit_badge(badge_value)

        single_hit = 1 #max_profit >= single_limit
        portfolio_hit = total_profit >= portfolio_limit

        log.info(
            f"Total Profit: {total_profit:.2f}  Threshold: {portfolio_limit:.2f}  Result: {'BREACH' if portfolio_hit else 'NO BREACH'}",
            source="ProfitMonitor",
        )
        log.info(
            f"Highest Single Profit: {max_profit:.2f}  Threshold: {single_limit:.2f}  Result: {'BREACH' if single_hit else 'NO BREACH'}",
            source="ProfitMonitor",
        )

        if single_hit or portfolio_hit:
            alert_msg = f"💰 Total profit is ${total_profit:.2f}."
            notification_result = None
            if self.should_notify():
                notif = cfg["notifications"]
                if notif.get("system"):
                    try:
                        from backend.core.xcom_core.sound_service import SoundService  # type: ignore

                        SoundService().play("frontend/static/sounds/profit_alert.mp3")
                    except Exception as e:
                        log.warning(
                            f"SoundService unavailable: {e}", source="ProfitMonitor"
                        )

                if notif.get("tts", True):
                    self.xcom_core.send_notification(
                        level="HIGH",
                        subject="Profit Ready to Harvest",
                        body=alert_msg,
                        initiator="ProfitMonitor",
                        mode="tts",
                    )
                if notif.get("voice"):
                    self.xcom_core.send_notification(
                        level="HIGH",
                        subject="Profit Ready to Harvest",
                        body=alert_msg,
                        initiator="ProfitMonitor",
                        mode="voice",
                    )
                if notif.get("sms"):
                    self.xcom_core.send_notification(
                        level="HIGH",
                        subject="Profit Ready to Harvest",
                        body=alert_msg,
                        initiator="ProfitMonitor",
                        mode="sms",
                    )

                log.success(
                    f"Profit alert sent: ${total_profit:.2f}.", source="ProfitMonitor"
                )
                self._set_silenced(False)
            else:
                log.info("Profit alert suppressed by snooze", source="ProfitMonitor")
                self._set_silenced(True)
            return {
                "alert_triggered": True,
                "total_profit": total_profit,
                "notification_result": notification_result,
            }

        log.info(
            f"No profit alert sent. Current profit: ${total_profit:.2f}.",
            source="ProfitMonitor",
        )
        self._set_silenced(False)
        return {
            "alert_triggered": False,
            "total_profit": total_profit,
        }

    def _update_profit_badge(self, badge_value):
        # Persist the badge value to align UI state
        self.dl.system.set_var("profit_badge_value", badge_value)

    def _set_silenced(self, state: bool) -> None:
        """Persist whether a profit alert was suppressed."""
        try:
            self.dl.system.set_var("profit_alert_silenced", bool(state))
        except Exception:
            pass
