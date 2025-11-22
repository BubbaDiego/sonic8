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

    This stores both metadata (type, avatar, notes) and secret material.
    """

    wallet_name: str
    wallet_type: str = "signer"  # "signer" or "view"

    public_key: Optional[str] = None

    # Secrets (signer wallets only)
    secret_base64: Optional[str] = None
    mnemonic_12: Optional[str] = None    # optional 12-word phrase
    passphrase: Optional[str] = None

    active: bool = True
    source: str = "config"      # e.g. "config", "env", "signer.txt"
    hint: Optional[str] = None  # non-sensitive human hint (no secrets!)

    # UX metadata
    avatar_path: Optional[str] = None
    notes: Optional[str] = None


class SignerStore:
    """
    Central store for wallet signing material.

    Backing sources (in priority order):

    1. JSON file pointed at by $SONIC_SIGNERS_JSON (if present), default:
       backend/core/wallet_core/signers.json

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
    DEFAULT_JSON_PATH = "backend/core/wallet_core/signers.json"

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
                log.warning("Skipping signer entry without wallet_name: %r", entry)
                continue

            rec = SignerRecord(
                wallet_name=name,
                wallet_type=str(entry.get("wallet_type", "signer")),
                public_key=entry.get("public_key"),
                secret_base64=entry.get("secret_base64"),
                mnemonic_12=entry.get("mnemonic_12"),
                passphrase=entry.get("passphrase"),
                active=bool(entry.get("active", True)),
                source=str(entry.get("source", "config")),
                hint=entry.get("hint"),
                avatar_path=entry.get("avatar_path"),
                notes=entry.get("notes"),
            )
            self._records[name] = rec

    def _save_to_json(self) -> None:
        """
        Persist the current records to the JSON file.

        The file format:

            {
              "wallets": [
                {
                  "wallet_name": "...",
                  "wallet_type": "signer" or "view",
                  "public_key": "...",
                  "avatar_path": "...",
                  "notes": "...",
                  "secret_base64": "...",
                  "mnemonic_12": "...",
                  "passphrase": "...",
                  "active": true,
                  "source": "wallet_core_console",
                  "hint": "..."
                },
                ...
              ]
            }
        """
        path_str = os.getenv(self.DEFAULT_JSON_ENV, self.DEFAULT_JSON_PATH)
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "wallets": [
                {
                    "wallet_name": rec.wallet_name,
                    "wallet_type": rec.wallet_type,
                    "public_key": rec.public_key,
                    "avatar_path": rec.avatar_path,
                    "notes": rec.notes,
                    "secret_base64": rec.secret_base64,
                    "mnemonic_12": rec.mnemonic_12,
                    "passphrase": rec.passphrase,
                    "active": rec.active,
                    "source": rec.source,
                    "hint": rec.hint,
                }
                for rec in sorted(self._records.values(), key=lambda r: r.wallet_name)
            ]
        }

        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def upsert_record(self, record: SignerRecord, *, persist: bool = True) -> SignerRecord:
        """
        Insert or update a SignerRecord in memory and optionally persist
        to signers.json.
        """
        self._ensure_loaded()
        self._records[record.wallet_name] = record
        if persist:
            self._save_to_json()
        return record
