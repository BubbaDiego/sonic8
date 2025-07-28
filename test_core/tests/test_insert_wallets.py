import os
import core.core_constants as const
from pathlib import Path
from data.data_locker import DataLocker
from scripts.insert_wallets import load_wallets, upsert_wallets

SEED_PATCHES = [
    "_seed_modifiers_if_empty",
    "_seed_wallets_if_empty",
    "_seed_thresholds_if_empty",
    "_seed_alerts_if_empty",
]

def setup_service(tmp_path, monkeypatch):
    db_path = tmp_path / "wallets.db"
    os.environ["MOTHER_DB_PATH"] = str(db_path)
    const.MOTHER_DB_PATH = db_path
    const.DB_PATH = db_path
    from wallets import wallet_repository
    monkeypatch.setattr(wallet_repository, "MOTHER_DB_PATH", db_path, raising=False)
    for name in SEED_PATCHES:
        monkeypatch.setattr(DataLocker, name, lambda self: None)
    from wallets.wallet_service import WalletService
    return WalletService()

def test_upsert_star_wars_wallets(tmp_path, monkeypatch, capsys):
    service = setup_service(tmp_path, monkeypatch)
    json_path = Path("wallets/test_wallets/star_wars_wallets.json")
    wallets = load_wallets(json_path)
    created, updated = upsert_wallets(wallets, service)
    capsys.readouterr()  # flush output
    assert created == len(wallets)
    assert updated == 0
    assert len(service.list_wallets()) == len(wallets)
