import pytest
from data.data_locker import DataLocker


def disable_seeding(monkeypatch):
    monkeypatch.setattr(DataLocker, "_seed_modifiers_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_wallets_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_thresholds_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alerts_if_empty", lambda self: None)


def _create_alert(dl, alert_id, status="Active"):
    alert = {
        "id": alert_id,
        "created_at": "2024-01-01T00:00:00",
        "alert_type": "PriceThreshold",
        "alert_class": "Market",
        "asset_type": "BTC",
        "trigger_value": 1.0,
        "condition": "ABOVE",
        "notification_type": "SMS",
        "level": "Normal",
        "last_triggered": None,
        "status": status,
        "frequency": 1,
        "counter": 0,
        "liquidation_distance": 0.0,
        "travel_percent": 0.0,
        "liquidation_price": 0.0,
        "notes": "",
        "description": "",
        "position_reference_id": None,
        "evaluated_value": None,
        "position_type": None,
    }
    dl.alerts.create_alert(alert)


def test_clear_inactive_alerts(tmp_path, monkeypatch):
    disable_seeding(monkeypatch)
    dl = DataLocker(str(tmp_path / "test.db"))

    _create_alert(dl, "a1", "Active")
    _create_alert(dl, "a2", "Expired")
    _create_alert(dl, "a3", None)

    assert len(dl.alerts.get_all_alerts()) == 3

    dl.alerts.clear_inactive_alerts()
    remaining = dl.alerts.get_all_alerts()

    assert len(remaining) == 1
    assert remaining[0]["id"] == "a1"
    dl.close()
