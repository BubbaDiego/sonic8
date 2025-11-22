from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SignerRecord:
    """
    In-memory representation of signing config for a wallet.

    This does *not* perform any Solana keypair parsing; it just
    stores the opaque secrets / passphrases that other code can use.
    """

    wallet_name: str
    public_key: Optional[str] = None
    secret_base64: Optional[str] = None
    passphrase: Optional[str] = None
    active: bool = True
    source: str = "config"      # e.g. "config", "env", "signer.txt"
    hint: Optional[str] = None  # non-sensitive human hint (no secrets!)


class SignerStore:
    """
    Central store for wallet signing material.

    Backing sources (in priority order):

    1. JSON file pointed at by $SONIC_SIGNERS_JSON (if present), default:
       backend/config/signers.json

       Format:
           {
             "wallets": [
               {
                 "wallet_name": "default",
                 "public_key": "...",
                 "secret_base64": "...",
                 "passphrase": null,
                 "active": true,
                 "hint": "Main trading wallet"
               }
             ]
           }

    2. Environment-based legacy wallet:
       - If `WALLET_SECRET_BASE64` is set, we expose a single wallet
         named "default" with that secret_base64, source="env".

    We do *not* handle signer.txt migration in this v1; existing
    signer.txt behaviour remains in the Jupiter/AutoCore helpers.
    """

    DEFAULT_JSON_ENV = "SONIC_SIGNERS_JSON"
    DEFAULT_JSON_PATH = "backend/config/signers.json"

    def __init__(self) -> None:
        self._records: Dict[str, SignerRecord] = {}
        self._loaded = False

    # --- public API -------------------------------------------------------

    def list_wallets(self, active_only: bool = True) -> List[SignerRecord]:
        self._ensure_loaded()
        records = list(self._records.values())
        if active_only:
            records = [r for r in records if r.active]
        return sorted(records, key=lambda r: r.wallet_name)

    def get(self, wallet_name: str) -> Optional[SignerRecord]:
        self._ensure_loaded()
        return self._records.get(wallet_name)

    def require(self, wallet_name: str) -> SignerRecord:
        rec = self.get(wallet_name)
        if rec is None:
            raise KeyError(f"Signer not configured for wallet_name={wallet_name!r}")
        return rec

    def get_default(self) -> Optional[SignerRecord]:
        """
        Return a 'default' signer, if any.

        Priority:
        - A record named 'default' in the JSON file.
        - Otherwise, if WALLET_SECRET_BASE64 is set, synthesize a
          'default' record from env.
        """
        self._ensure_loaded()

        if "default" in self._records:
            return self._records["default"]

        # fallback legacy env path
        env_secret = os.getenv("WALLET_SECRET_BASE64")
        if env_secret:
            return SignerRecord(
                wallet_name="default",
                secret_base64=env_secret,
                active=True,
                source="env",
                hint="WALLET_SECRET_BASE64",
            )

        return None

    # --- internal loading -------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._records = {}
        self._load_from_json()
        # no JSON? still allow env-only fallback via get_default
        self._loaded = True

    def _load_from_json(self) -> None:
        path_str = os.getenv(self.DEFAULT_JSON_ENV, self.DEFAULT_JSON_PATH)
        path = Path(path_str)
        if not path.exists():
            log.info("SignerStore JSON file not found at %s; using env-only config", path)
            return

        try:
            raw = json.loads(path.read_text(encoding="utf-8") or "{}")
        except Exception:
            log.exception("Failed to parse signer store JSON at %s", path)
            return

        wallets = raw.get("wallets", [])
        for entry in wallets:
            try:
                name = str(entry["wallet_name"])
            except KeyError:
                log.warning("Skipping signer entry missing wallet_name key: %r", entry)
                continue

            rec = SignerRecord(
                wallet_name=name,
                public_key=entry.get("public_key"),
                secret_base64=entry.get("secret_base64"),
                passphrase=entry.get("passphrase"),
                active=bool(entry.get("active", True)),
                source=str(entry.get("source", "config")),
                hint=entry.get("hint"),
            )
            self._records[name] = rec
