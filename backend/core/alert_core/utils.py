from core.locker_factory import get_locker
from core.logging import log
from data.alert import (
    AlertType,
    NotificationType,
    Condition as AlertCondition,
)


# --- Normalization helpers -------------------------------------------------

def normalize_alert_fields(alert):
    """Normalize enum fields on an alert object or dict."""
    if isinstance(alert, dict):
        if "alert_type" in alert:
            alert["alert_type"] = normalize_alert_type(alert["alert_type"])
        if "condition" in alert:
            alert["condition"] = normalize_condition(alert["condition"])
        if "notification_type" in alert:
            alert["notification_type"] = normalize_notification_type(alert["notification_type"])
        return alert

    if hasattr(alert, "alert_type") and alert.alert_type:
        alert.alert_type = normalize_alert_type(alert.alert_type)
    if hasattr(alert, "condition") and alert.condition:
        alert.condition = normalize_condition(alert.condition)
    if hasattr(alert, "notification_type") and alert.notification_type:
        alert.notification_type = normalize_notification_type(alert.notification_type)
    return alert


def normalize_condition(condition_input):
    if isinstance(condition_input, AlertCondition):
        return condition_input
    if isinstance(condition_input, str):
        cleaned = condition_input.strip().replace("_", "").replace(" ", "").lower()
        mapping = {
            "above": AlertCondition.ABOVE,
            "below": AlertCondition.BELOW,
        }
        if cleaned in mapping:
            return mapping[cleaned]
        raise ValueError(f"Invalid condition string: {condition_input}")
    raise TypeError(f"Invalid condition input: {type(condition_input)}")


def resolve_wallet_metadata(alert, data_locker=None):
    if not alert or not getattr(alert, "position_reference_id", None):
        return {"wallet_name": None, "wallet_image": None, "wallet_id": None}

    data_locker = data_locker or get_locker()
    position = data_locker.get_position_by_reference_id(alert.position_reference_id)
    if not position:
        return {"wallet_name": None, "wallet_image": None, "wallet_id": None}

    wallet_name = position.get("wallet_name") or position.get("wallet")
    wallet_id = position.get("wallet_id")

    wallet = data_locker.get_wallet_by_name(wallet_name) if wallet_name else None
    return {
        "wallet_name": wallet.get("name") if wallet else wallet_name,
        "wallet_image": wallet.get("image_path") if wallet else f"/static/images/{wallet_name.lower()}.jpg",
        "wallet_id": wallet_id,
    }


def normalize_alert_type(alert_type_input):
    if isinstance(alert_type_input, AlertType):
        return alert_type_input
    if isinstance(alert_type_input, str):
        cleaned = alert_type_input.strip().replace("_", "").replace(" ", "").lower()
        mapping = {
            "pricethreshold": AlertType.PriceThreshold,
            "profit": AlertType.Profit,
            "travelpercentliquid": AlertType.TravelPercentLiquid,
            "travelpercent": AlertType.TravelPercent,
            "heatindex": AlertType.HeatIndex,
            "deathnail": AlertType.DeathNail,
            "totalvalue": AlertType.TotalValue,
            "totalsize": AlertType.TotalSize,
            "avgleverage": AlertType.AvgLeverage,
            "avgtravelpercent": AlertType.AvgTravelPercent,
            "valuetocollateralratio": AlertType.ValueToCollateralRatio,
            "totalheat": AlertType.TotalHeat,
        }
        if cleaned in mapping:
            return mapping[cleaned]
        raise ValueError(
            f"Invalid alert_type string: {alert_type_input}. Expected one of: {list(mapping.keys())}"
        )
    raise TypeError(f"Invalid alert_type input: {type(alert_type_input)}")


def normalize_notification_type(notification_input):
    if isinstance(notification_input, NotificationType):
        return notification_input
    if isinstance(notification_input, str):
        cleaned = notification_input.strip().replace("_", "").replace(" ", "").lower()
        mapping = {
            "sms": NotificationType.SMS,
            "email": NotificationType.EMAIL,
            "phonecall": NotificationType.PHONECALL,
        }
        if cleaned in mapping:
            return mapping[cleaned]
        raise ValueError(f"Invalid notification_type string: {notification_input}")
    raise TypeError(f"Invalid notification_type input: {type(notification_input)}")


def log_alert_summary(alert):
    alert_type = alert.get("alert_type") if isinstance(alert, dict) else getattr(alert, "alert_type", None)
    alert_class = alert.get("alert_class") if isinstance(alert, dict) else getattr(alert, "alert_class", None)
    trigger_value = alert.get("trigger_value") if isinstance(alert, dict) else getattr(alert, "trigger_value", None)

    print(f"\N{PACKAGE} Alert Created \u2192 \N{COMPASS} Class: {alert_class} | \N{LABEL} Type: {alert_type} | \N{DIRECT HIT} Trigger: {trigger_value}")

    if isinstance(alert, dict):
        log.info(
            f"\N{PACKAGE} Alert Created \u2192 \N{COMPASS} Class: {alert_class} | \N{LABEL} Type: {alert_type} | \N{DIRECT HIT} Trigger: {trigger_value}",
            source="CreateAlert",
        )


def load_alert_thresholds_from_file(data_locker):
    from config.config_loader import load_config
    from core.constants import ALERT_THRESHOLDS_PATH

    config = load_config(str(ALERT_THRESHOLDS_PATH))
    if not config:
        raise RuntimeError("\N{NO ENTRY} Config file is invalid or empty")

    data_locker.system.set_var("alert_thresholds", config)
    log.success("\N{WHITE HEAVY CHECK MARK} Loaded alert_thresholds config into DB from file", source="ConfigImport")
    return config


__all__ = [
    "resolve_wallet_metadata",
    "log_alert_summary",
    "normalize_alert_fields",
]
