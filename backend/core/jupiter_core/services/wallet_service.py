from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Optional

from ..config import JupiterConfig, get_config


class WalletService:
    """Utility helpers for reading a mnemonic and deriving a Solana pubkey."""

    def __init__(self, cfg: Optional[JupiterConfig] = None) -> None:
        self.cfg = cfg or get_config()

    # ---------- public API ----------
    def read_signer_info(self) -> Dict[str, str]:
        signer_path = self._resolve_signer_path()
        mnemonic = self._read_mnemonic(signer_path)
        pubkey_b58 = self._derive_pubkey_b58(mnemonic, self.cfg.solana_derivation_path)
        return {
            "signer_path": str(signer_path),
            "derivation_path": self.cfg.solana_derivation_path,
            "public_key": pubkey_b58,
            "mnemonic_words": str(len(mnemonic.split())),
        }

    # ---------- internals ----------
    def _resolve_signer_path(self) -> Path:
        # 1) explicit env override
        if self.cfg.signer_path:
            path = Path(self.cfg.signer_path).expanduser()
            if path.exists():
                return path

        # 2) cwd
        cwd = Path(os.getcwd())
        if (cwd / "signer.txt").exists():
            return cwd / "signer.txt"

        # 3) ascend looking for repo root (contains "backend")
        here = Path(__file__).resolve()
        probe = here
        for _ in range(6):
            if (probe / "backend").exists() and (probe / "signer.txt").exists():
                return probe / "signer.txt"
            probe = probe.parent

        # 4) last-ditch: repo root inferred from backend path
        guess = here.parents[4] / "signer.txt"
        if guess.exists():
            return guess

        raise FileNotFoundError(
            "signer.txt not found. Set SIGNER_PATH or place it at repo root."
        )

    def _read_mnemonic(self, signer_path: Path) -> str:
        txt = signer_path.read_text(encoding="utf-8", errors="ignore").strip()
        # Allow formats:
        #   passphrase=one two three ...
        #   mnemonic: one two ...
        #   plain line with 12/24 words
        match = re.search(r"(?:passphrase|mnemonic)\s*[:=]\s*(.+)", txt, re.IGNORECASE)
        if match:
            phrase = match.group(1).strip().strip('"').strip("'")
        else:
            # take the first long-ish word line
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            if not lines:
                raise ValueError("signer.txt is empty")
            phrase = lines[0]

        words = phrase.split()
        if len(words) < 12:
            raise ValueError("signer.txt does not contain a valid 12/24-word mnemonic")
        return " ".join(words)

    def _derive_pubkey_b58(self, mnemonic: str, path: str) -> str:
        # Lazy imports with friendly errors
        try:
            from bip_utils import Bip39SeedGenerator, Slip10Ed25519
            from nacl.signing import SigningKey
            import base58  # type: ignore
        except Exception as exc:  # pragma: no cover - import-time environment issues
            raise RuntimeError(
                "Missing crypto deps. Install: pip install bip_utils pynacl base58"
            ) from exc

        seed = Bip39SeedGenerator(mnemonic).Generate()
        slip = Slip10Ed25519.FromSeedAndPath(seed, path)
        priv_key = slip.PrivateKey().Raw().ToBytes()  # 32 bytes
        # Derive public key via NaCl (ed25519)
        pub_key = SigningKey(priv_key).verify_key.encode()  # 32 bytes
        return base58.b58encode(pub_key).decode("ascii")
