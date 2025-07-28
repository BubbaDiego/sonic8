import random
import sys
from backend.utils.time_utils import iso_utc_now

from typing import List, Dict

from backend.core.constants import MOTHER_DB_PATH
from backend.core.core_imports import configure_console_log
from backend.data.data_locker import DataLocker
from backend.core.oracle_core.persona_manager import PersonaManager
from backend.core.trader_core.persona_avatars import AVATARS

# Static wallet definitions for Star Wars characters
STAR_WARS_WALLETS: List[Dict] = [
    {
        "name": "BobaVault",
        "image": "images/boba_icon.jpg",
        "public": "9DXTA7dnFjEKVq6d5v7X79C35VzuFUhZUi5PRceKLYNa",
        "passphrase": "flavor armor amused permit funny unusual ensure pull race street waste dash",
    },
    {
        "name": "C3P0Vault",
        "image": "images/c3p0_icon.jpg",
        "public": "72nSXTTCUmYad6gFmzULcTmEJva9wNpg4MUovyvnZezQ",
        "passphrase": "mouse orange bike opinion swamp weather cram scrap best buddy prefer order",
    },
    {
        "name": "JabbaVault",
        "image": "images/jabba_icon.jpg",
        "public": "BB4SvFPPqyV5sQD6Pb1sWmvhinh8QYjRpGk9SkW8USsT",
        "passphrase": "squirrel urge portion father desert future admit light culture all neck risk",
    },
    {
        "name": "LandoVault",
        "image": "images/lando_icon.jpg",
        "public": "6vMjsGU63evYuwwGsDHBRnKs1stALR7SYN5V57VZLXca",
        "passphrase": "trap rich grid fork fat horn next dial cash any maid cave yard wage bean coil age taxi lion farm feel pear fade black",
    },
    {
        "name": "LeiaVault",
        "image": "images/leia_icon.jpg",
        "public": "BrgzPKzjkTydKAaibaVn1dgjgSmzT9D8VYR9tyLhctxm",
        "passphrase": "gravity orient angle snack fancy vacuum damp cry game account gasp immune",
    },
    {
        "name": "LukeVault",
        "image": "images/luke_icon.jpg",
        "public": "CQ6NhW8TULZAhXPgUR5AP81rKt6CKFGizDaDsXHmd8ih",
        "passphrase": "club bicycle grunt satisfy above setup bulb shuffle odor rigid assist harsh",
    },
    {
        "name": "PalpatineVault",
        "image": "images/palpatine_icon.jpg",
        "public": "CiPiaEJQzp44Cv6UVGecPzPMqx6KHHSse8ZoVqnmT4hP",
        "passphrase": "fortune egg birth regret hair bleak observe step equip monster invest bullet",
    },
    {
        "name": "R2D2Vault",
        "image": "images/r2d2_icon.jpg",
        "public": "5puBV83X2E9dw5MBiQX3T5cjAL9XVi7SucGQZLWZmbh3",
        "passphrase": "render unaware indicate clerk amount pool guide want doctor ramp cushion spread",
    },
    {
        "name": "VaderVault",
        "image": "images/vader_icon.jpg",
        "public": "E5cVX6nYE4KWGic7qfbyP1SPkdUvT6aqXFQkGYPxQCta",
        "passphrase": "promote diesel mail stock marriage half very slight miracle mom drill february",
    },
    {
        "name": "YodaVault",
        "image": "images/yoda_icon.jpg",
        "public": "CofTLEqPUXscsigdvP8YWkRTDmCQ6W7GKBVKRsZ6UvLn",
        "passphrase": "wonder smile potato fat turn problem girl gather nose venture square fox",
    },
]

# Mapping from wallet names to persona names when they differ
WALLET_PERSONA_MAP = {
    "R2D2Vault": "R2",
}

MOOD_WORDS = [
    "nervous",
    "roaring",
    "ruthless",
    "charming",
    "resolute",
    "determined",
    "power_hungry",
    "beeping",
    "calm",
]


def insert_star_wars_traders() -> int:
    """Create traders for Star Wars personas and persist them."""
    configure_console_log()
    locker = DataLocker(str(MOTHER_DB_PATH))
    pm = PersonaManager()
    created = 0

    for info in STAR_WARS_WALLETS:
        wallet_name = info["name"]
        persona_name = WALLET_PERSONA_MAP.get(wallet_name, wallet_name.replace("Vault", ""))
        try:
            persona = pm.get(persona_name)
        except KeyError:
            # Skip wallets without a matching persona
            continue

        wallet = locker.wallets.get_wallet_by_name(wallet_name)
        balance = wallet.get("balance", 0.0) if wallet else 0.0

        avatar_key = getattr(persona, "avatar", persona.name)
        avatar = AVATARS.get(avatar_key, {}).get("icon", avatar_key)
        mood1, mood2 = random.sample(MOOD_WORDS, 2)
        data = {
            "name": persona.name,
            "avatar": avatar,
            "color": getattr(persona, "color", ""),
            "wallet": wallet_name,
            "born_on": iso_utc_now(),
            "initial_collateral": balance,
            "mood": mood1,
            "moods": {"high_heat": mood1, "stable": mood2},
        }
        try:
            locker.traders.create_trader(data)
            created += 1
            print(f"Inserted trader: {persona.name}")
        except Exception as exc:  # pragma: no cover - best effort
            print(f"Failed to create trader {persona.name}: {exc}")

    locker.close()
    print(f"All traders inserted: {created}")
    return created


if __name__ == "__main__":  # pragma: no cover - manual execution
    insert_star_wars_traders()
