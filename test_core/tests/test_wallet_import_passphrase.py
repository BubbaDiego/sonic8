import os
import importlib
import core.constants as const
import core.core_imports as ci
from data.data_locker import DataLocker
import wallets.wallet_service  # ensure module is importable for reload

SEED_PATCHES = [
    "_seed_modifiers_if_empty",
    "_seed_wallets_if_empty",
    "_seed_thresholds_if_empty",
    "_seed_alerts_if_empty",
]


def setup_service(tmp_path, monkeypatch):
    db_path = tmp_path / "passphrase.db"
    os.environ["MOTHER_DB_PATH"] = str(db_path)
    const.MOTHER_DB_PATH = db_path
    const.DB_PATH = db_path
    ci.MOTHER_DB_PATH = db_path
    ci.DB_PATH = db_path
    from wallets import wallet_repository
    importlib.reload(wallet_repository)
    monkeypatch.setattr(wallet_repository, "MOTHER_DB_PATH", db_path, raising=False)
    # Reset DataLocker singleton to avoid cross-test leakage
    DataLocker._instance = None
    for name in SEED_PATCHES:
        monkeypatch.setattr(DataLocker, name, lambda self: None)
    from wallets.wallet_service import WalletService
    importlib.reload(wallets.wallet_service)
    return WalletService()


def test_import_wallets_from_json_with_passphrase(tmp_path, monkeypatch):
    service = setup_service(tmp_path, monkeypatch)
    os.environ["WALLET_ENCRYPTION_KEY"] = "sixteenbytekey!!"
    os.environ["BOBA_PASSPHRASE"] = "boba-secret"
    os.environ["C3P0_PASSPHRASE"] = "c3po-secret"

    count = service.import_wallets_from_json()
    assert count == 10

    boba = service.repo.get_wallet_by_name("BobaVault")
    c3p0 = service.repo.get_wallet_by_name("C3P0Vault")
    lando = service.repo.get_wallet_by_name("LandoVault")

    assert boba.private_address == "boba-secret"
    assert c3p0.private_address == "c3po-secret"
    assert lando.private_address is None
    DataLocker._instance = None
    os.environ["MOTHER_DB_PATH"] = "/tmp/test_wallet.db"
    const.MOTHER_DB_PATH = "/tmp/test_wallet.db"
    const.DB_PATH = "/tmp/test_wallet.db"
    ci.MOTHER_DB_PATH = "/tmp/test_wallet.db"
    ci.DB_PATH = "/tmp/test_wallet.db"
