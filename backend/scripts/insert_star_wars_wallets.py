import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Dynamically build the wallet path relative to the script
wallet_json_path = os.path.join(os.path.dirname(__file__), '..', 'wallets', 'test_wallets', 'star_wars_wallets.json')

from backend.core.wallet_core import WalletCore
from backend.models.wallet import Wallet

def insert_star_wars_wallets() -> int:
    """Insert Star Wars wallets defined in ``wallet_json_path``."""
    try:
        with open(wallet_json_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"❌ File not found: {wallet_json_path}")
        return 0

    wallet_core = WalletCore()
    inserted = 0
    for wallet_info in data['wallets']:
        wallet = Wallet(
            name=wallet_info['name'],
            public_address=wallet_info['public_address'],
            private_address=wallet_info.get('private_address'),
            image_path=wallet_info['image_path'],
            tags=["star_wars", "imported"],
            is_active=True,
            type="personal"
        )

        try:
            wallet_core.service.create_wallet(wallet)
            inserted += 1
            print(f"✅ Inserted wallet: {wallet.name}")
        except ValueError as e:
            print(f"⚠️ Skipped wallet '{wallet.name}': {e}")

    print("✅ Wallet insertion completed.")
    return inserted


if __name__ == "__main__":
    insert_star_wars_wallets()
