from __future__ import annotations

import binascii
import hashlib
import os
from typing import Optional

def _disc_from_name(name: str) -> bytes:
    # Anchor discriminator = first 8 bytes of sha256(b"account:" + name)
    return hashlib.sha256(f"account:{name}".encode("utf-8")).digest()[:8]


def get_disc(role: str, default_account_name: str) -> bytes:
    """
    Resolve the anchor discriminator for a given role ("pool", "custody", "position").

    Priority:
      1) PERPS_<ROLE>_DISC (hex string, e.g., '0x0102030405060708' or '010203...')
      2) PERPS_<ROLE>_ACCOUNT_NAME (string) -> sha256("account:"+name)[:8]
      3) default_account_name (string)
    """
    env_hex = (os.getenv(f"PERPS_{role.upper()}_DISC") or "").strip()
    if env_hex:
        s = env_hex.lower().replace("0x", "").replace(" ", "")
        return binascii.unhexlify(s)

    name = (os.getenv(f"PERPS_{role.upper()}_ACCOUNT_NAME") or default_account_name).strip()
    return _disc_from_name(name)


def get_account_name(role: str, default_account_name: str) -> str:
    """
    Return the configured account name for debugging/trace.
    """
    return (os.getenv(f"PERPS_{role.upper()}_ACCOUNT_NAME") or default_account_name).strip()
