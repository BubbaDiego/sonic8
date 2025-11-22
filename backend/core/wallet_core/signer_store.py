from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class WalletSigner:
    """
    In-memory representation of signing credentials for a single wallet.

    NOTE: Do not log secret material. Logging helpers in this module must
    only ever include wallet_id / label / public_key.
    """

    wallet_id: str
    public_key: str
    secret_base64: Optional[str] = None
    passphrase: Optional[str] = None
    label: Optional[str] = None
    active: bool = True


class SignerStore:
    """
    File-backed store for wallet signing credentials.

    The default backing file is JSON with the following shape:

        {
          "wallets": [
            {
              "wallet_id": "main",
              "public_key": "....",
              "secret_base64": "....",   # optional
              "passphrase": "....",      # optional
              "label": "Main trading wallet",
              "active": true
            },
            ...
          ]
        }

    The **only** thing this module does is load & filter these records.
    It does NOT write secrets back to disk.
    """

    DEFAULT_ENV_KEY = "SONIC_SIGNERS_PATH"
    DEFAULT_RELATIVE_PATH = "backend/config/signers.json"

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._cache: Dict[str, WalletSigner] = {}
        self._loaded: bool = False

    # ---- construction helpers -------------------------------------------------

    @classmethod
    def from_env(cls) -> "SignerStore":
        """
        Construct a SignerStore using:

        - $SONIC_SIGNERS_PATH if set
        - otherwise the default relative path under the repo root
          (backend/config/signers.json)
        """
        path_str = os.getenv(cls.DEFAULT_ENV_KEY, cls.DEFAULT_RELATIVE_PATH)
        return cls(Path(path_str))

    # ---- internal loading ------------------------------------------------------

    def _load_if_needed(self) -> None:
        if self._loaded:
            return

        if not self._path.exists():
            log.warning("SignerStore path does not exist: %s", self._path)
            self._cache = {}
            self._loaded = True
            return

        try:
            text = self._path.read_text(encoding="utf-8")
            raw = json.loads(text or "{}")
        except Exception:
            # Fail closed: no signers if the file is unreadable / invalid JSON.
            log.exception("Failed to load signers file at %s", self._path)
            self._cache = {}
            self._loaded = True
            return

        wallets = raw.get("wallets", [])
        cache: Dict[str, WalletSigner] = {}

        for entry in wallets:
            try:
                signer = WalletSigner(
                    wallet_id=str(entry["wallet_id"]),
                    public_key=str(entry["public_key"]),
                    secret_base64=entry.get("secret_base64"),
                    passphrase=entry.get("passphrase"),
                    label=entry.get("label"),
                    active=bool(entry.get("active", True)),
                )
            except KeyError as exc:
                log.warning(
                    "Skipping malformed signer entry in %s (missing %s)",
                    self._path,
                    exc,
                )
                continue

            cache[signer.wallet_id] = signer

        self._cache = cache
        self._loaded = True

    # ---- public API ------------------------------------------------------------

    def list_signers(self, active_only: bool = False) -> List[WalletSigner]:
        """
        Return all configured signers.

        :param active_only: if True, filter to signers with active=True
        """
        self._load_if_needed()
        signers = list(self._cache.values())
        if not active_only:
            return signers
        return [s for s in signers if s.active]

    def get_signer(self, wallet_id: str) -> Optional[WalletSigner]:
        """Return the signer for a wallet_id, or None if not configured."""
        self._load_if_needed()
        return self._cache.get(wallet_id)

    def require_signer(self, wallet_id: str) -> WalletSigner:
        """
        Return the signer for wallet_id, raising KeyError if it does not exist.

        This is the method WalletCore should use when the signer is required
        to proceed with an operation.
        """
        signer = self.get_signer(wallet_id)
        if signer is None:
            raise KeyError(f"No signer configured for wallet_id={wallet_id!r}")
        return signer

    def get_default_signer(self) -> Optional[WalletSigner]:
        """
        Convenience for callers that conceptually have a single 'default'
        wallet. Returns the first active signer if any, else None.
        """
        actives = self.list_signers(active_only=True)
        return actives[0] if actives else None


__all__ = ["WalletSigner", "SignerStore"]
