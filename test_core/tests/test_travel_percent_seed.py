import os
import sqlite3

from data.data_locker import DataLocker


def disable_other_seeds(monkeypatch):
    monkeypatch.setattr(DataLocker, "_seed_modifiers_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_wallets_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alerts_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_thresholds_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alert_config_if_empty", lambda self: None)

import importlib

import data.data_locker as dl_module


def disable_other_seeds(monkeypatch):
    global dl_module
    # Reload the module in case another test replaced DataLocker with a stub.
    if not hasattr(dl_module.DataLocker, "_seed_modifiers_if_empty"):
        dl_module = importlib.reload(dl_module)

    DataLockerCls = dl_module.DataLocker

    monkeypatch.setattr(DataLockerCls, "_seed_modifiers_if_empty", lambda self: None)
    monkeypatch.setattr(DataLockerCls, "_seed_wallets_if_empty", lambda self: None)
    monkeypatch.setattr(DataLockerCls, "_seed_alerts_if_empty", lambda self: None)
    monkeypatch.setattr(DataLockerCls, "_seed_thresholds_if_empty", lambda self: None)
    monkeypatch.setattr(DataLockerCls, "_seed_alert_config_if_empty", lambda self: None)



def test_travel_percent_threshold_seeded(tmp_path, monkeypatch):
    disable_other_seeds(monkeypatch)
    db_path = tmp_path / "thr.db"

    dl = dl_module.DataLocker(str(db_path))

    cursor = dl.db.get_cursor()
    count = cursor.execute(
        "SELECT COUNT(*) FROM alert_thresholds WHERE alert_type='TravelPercent'"
    ).fetchone()[0]
    dl.close()
    assert count == 1
