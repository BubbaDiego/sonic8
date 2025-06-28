from data.data_locker import DataLocker
from cyclone.cyclone_maintenance_service import CycloneMaintenanceService


def _patch_seeding(monkeypatch):
    monkeypatch.setattr(DataLocker, "_seed_modifiers_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_wallets_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_thresholds_if_empty", lambda self: None)
    monkeypatch.setattr(DataLocker, "_seed_alerts_if_empty", lambda self: None)


def test_clear_positions_resets_profit_badge(tmp_path, monkeypatch):
    _patch_seeding(monkeypatch)
    dl = DataLocker(str(tmp_path / "test.db"))
    dl.system.set_var("profit_badge_value", 123)

    maint = CycloneMaintenanceService(dl)
    maint.clear_positions()

    assert dl.system.get_var("profit_badge_value") is None
    dl.db.close()
