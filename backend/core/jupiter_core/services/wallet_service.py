from __future__ import annotations

import hashlib
import hmac
import os
import re
import struct
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import base58
import requests
from nacl.signing import SigningKey

from ..config import JupiterConfig, get_config


class WalletService:
    """Utility helpers for reading signer.txt and deriving a Solana pubkey."""

    def __init__(self, cfg: Optional[JupiterConfig] = None) -> None:
        self.cfg = cfg or get_config()

    # ---------- public API ----------
    def read_signer_info(self) -> Dict[str, str]:
        signer_path = self._resolve_signer_path()
        mnemonic, bip39_pass = self._read_signer_text(signer_path)
        pubkey_b58 = self._derive_pubkey_b58(
            mnemonic, self.cfg.solana_derivation_path, bip39_pass
        )
        return {
            "signer_path": str(signer_path),
            "derivation_path": self.cfg.solana_derivation_path,
            "public_key": pubkey_b58,
            "mnemonic_words": str(len(mnemonic.split())),
            "bip39_passphrase": "yes" if bip39_pass else "no",
        }

    def fetch_sol_balance(self, public_key: str) -> Dict[str, object]:
        """Return {"lamports": int, "sol": float} using JSON-RPC getBalance."""

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [public_key, {"commitment": "processed"}],
            }
            resp = requests.post(self.cfg.solana_rpc_url, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            lamports = int(data["result"]["value"])
            return {"lamports": lamports, "sol": lamports / 1_000_000_000}
        except Exception as exc:  # pragma: no cover - network failure
            return {"error": f"{type(exc).__name__}: {exc}"}

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

        # 3) ascend looking for repo root (contains "backend") + signer.txt
        here = Path(__file__).resolve()
        probe = here
        for _ in range(8):
            if (probe / "backend").exists() and (probe / "signer.txt").exists():
                return probe / "signer.txt"
            probe = probe.parent

        # 4) last guess: repo root parent of backend
        guess = here.parents[4] / "signer.txt"
        if guess.exists():
            return guess

        raise FileNotFoundError(
            "signer.txt not found. Set SIGNER_PATH or place at repo root."
        )

    def _read_signer_text(self, signer_path: Path) -> Tuple[str, str]:
        """
        Accepts any of:
          passphrase=word1 word2 ...
          mnemonic: word1 word2 ...
          (or) first non-empty line with 12/24 words
        Optional BIP39 passphrase lines:
          bip39_passphrase=your phrase
          seed_passphrase: your phrase
        """

        txt = signer_path.read_text(encoding="utf-8", errors="ignore").strip()

        # Extract mnemonic
        match = re.search(r"(?:passphrase|mnemonic)\s*[:=]\s*(.+)", txt, re.IGNORECASE)
        if match:
            mnemonic = match.group(1).strip().strip('"').strip("'")
        else:
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            if not lines:
                raise ValueError("signer.txt is empty")
            mnemonic = lines[0]

        words = mnemonic.split()
        if len(words) < 12:
            raise ValueError("signer.txt does not contain a valid 12/24-word mnemonic")

        # Optional BIP39 passphrase
        passphrase_match = re.search(
            r"(?:bip39_passphrase|seed_passphrase)\s*[:=]\s*(.+)",
            txt,
            re.IGNORECASE,
        )
        bip39_pass = ""
        if passphrase_match:
            bip39_pass = passphrase_match.group(1).strip().strip('"').strip("'")

        return " ".join(words), bip39_pass

    # --- crypto helpers (pure Python) --------------------------------------
    @staticmethod
    def _normalize_nfkd(value: str) -> str:
        return unicodedata.normalize("NFKD", value)

    def _bip39_seed(self, mnemonic: str, passphrase: str = "") -> bytes:
        # BIP-39 seed = PBKDF2-HMAC-SHA512(mnemonic, "mnemonic"+passphrase, 2048)
        mnemonic_norm = self._normalize_nfkd(mnemonic)
        salt = "mnemonic" + self._normalize_nfkd(passphrase or "")
        return hashlib.pbkdf2_hmac(
            "sha512",
            mnemonic_norm.encode("utf-8"),
            salt.encode("utf-8"),
            2048,
            dklen=64,
        )

    @staticmethod
    def _parse_path(path: str) -> List[int]:
        """
        Parse "m/44'/501'/0'/0'" -> [44'|0x80000000, 501'|..., 0'|..., 0'|...]
        Non-hardened segments are treated as hardened for ed25519 (common Solana convention).
        """

        if not path or not path.startswith("m/"):
            raise ValueError(f"Invalid derivation path: {path}")
        indices: List[int] = []
        for part in path[2:].split("/"):
            if not part:
                continue
            digits = part.rstrip("'hH")
            if not digits.isdigit():
                raise ValueError(f"Bad path segment: {part}")
            idx = int(digits)
            if idx < 0 or idx > 0x7FFFFFFF:
                raise ValueError(f"Path index out of range: {idx}")
            # For ed25519 hardened derivation only, force the bit regardless of suffix.
            indices.append(idx | 0x80000000)
        return indices

    @staticmethod
    def _slip10_ed25519_derive(seed: bytes, path_idx: List[int]) -> Tuple[bytes, bytes]:
        """
        SLIP-0010 master & child key derivation for ed25519.
        Returns (private_key32, chain_code32).
        """

        def hmac512(key: bytes, data: bytes) -> bytes:
            return hmac.new(key, data, hashlib.sha512).digest()

        # Master
        digest = hmac512(b"ed25519 seed", seed)
        key, chain_code = digest[:32], digest[32:]

        # Children (hardened only)
        for index in path_idx:
            data = b"\x00" + key + struct.pack(">L", index)
            digest = hmac512(chain_code, data)
            key, chain_code = digest[:32], digest[32:]
        return key, chain_code

    def _derive_pubkey_b58(
        self, mnemonic: str, path: str, bip39_passphrase: str = ""
    ) -> str:
        seed = self._bip39_seed(mnemonic, bip39_passphrase)
        key, _chain = self._slip10_ed25519_derive(seed, self._parse_path(path))
        pub_key = SigningKey(key).verify_key.encode()
        return base58.b58encode(pub_key).decode("ascii")
