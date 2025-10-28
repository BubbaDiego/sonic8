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
        """Return ``{"lamports": int, "sol": float}`` using ``getBalance``."""

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

    def fetch_spl_balance(self, public_key: str, mint: str) -> Dict[str, object]:
        """
        Fetch SPL token accounts for ``public_key`` filtered by ``mint`` and
        sum their balances. The result mirrors the common JSON-RPC response
        fields so the console can display UI amounts.
        """

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    public_key,
                    {"mint": mint},
                    {"encoding": "jsonParsed", "commitment": "processed"},
                ],
            }
            resp = requests.post(self.cfg.solana_rpc_url, json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            total_amount = 0
            decimals: Optional[int] = None
            for item in data.get("result", {}).get("value", []):
                info = item.get("account", {}).get("data", {}).get("parsed", {}).get(
                    "info", {}
                )
                token_amount = info.get("tokenAmount", {})
                amount = int(token_amount.get("amount", "0"))
                dec = int(token_amount.get("decimals", 0))
                total_amount += amount
                decimals = dec

            if decimals is None:
                decimals = self._fetch_mint_decimals(mint)

            if decimals is None:
                decimals = 0

            ui_amount = total_amount / (10 ** decimals) if decimals is not None else 0.0
            return {
                "mint": mint,
                "amount": total_amount,
                "decimals": decimals,
                "uiAmount": ui_amount,
            }
        except Exception as exc:  # pragma: no cover - network failure
            return {"mint": mint, "error": f"{type(exc).__name__}: {exc}"}

    def _fetch_mint_decimals(self, mint: str) -> Optional[int]:
        """Best-effort fetch of mint decimals when no token accounts exist."""

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenSupply",
                "params": [mint, {"commitment": "processed"}],
            }
            resp = requests.post(self.cfg.solana_rpc_url, json=payload, timeout=10)
            resp.raise_for_status()
            value = resp.json().get("result", {}).get("value")
            decimals = value.get("decimals") if isinstance(value, dict) else None
            return int(decimals) if isinstance(decimals, int) else None
        except Exception:  # pragma: no cover - depends on RPC availability
            return None

    def fetch_standard_balances(self, public_key: str) -> Dict[str, object]:
        """Fetch SOL plus a default basket of SPL tokens for convenience."""

        return {
            "SOL": self.fetch_sol_balance(public_key),
            "WSOL": self.fetch_spl_balance(public_key, self.cfg.wsol_mint),
            "WETH": self.fetch_spl_balance(public_key, self.cfg.weth_mint),
            "WBTC": self.fetch_spl_balance(public_key, self.cfg.wbtc_mint),
            "USDC": self.fetch_spl_balance(public_key, self.cfg.usdc_mint),
        }

    # --- signing & submission -----------------------------------------------
    def sign_tx_base64(self, unsigned_b64: str) -> str:
        """
        Best-effort transaction signer.

        Attempts to use ``solders`` (``VersionedTransaction``) first and falls back to
        ``solana-py`` legacy transactions. If neither library is available a helpful
        error is raised so the console can prompt for manual signing.
        """

        mnemonic, bip39_pass = self._read_signer_text(self._resolve_signer_path())
        seed = self._bip39_seed(mnemonic, bip39_pass)
        priv_key, _chain = self._slip10_ed25519_derive(
            seed, self._parse_path(self.cfg.solana_derivation_path)
        )

        # solders (preferred)
        try:
            import base64 as _b64
            from solders.keypair import Keypair  # type: ignore
            from solders.transaction import VersionedTransaction  # type: ignore

            keypair = Keypair.from_seed(priv_key)
            raw = _b64.b64decode(unsigned_b64)
            tx = VersionedTransaction.from_bytes(raw)
            signed = tx.sign([keypair])
            return _b64.b64encode(bytes(signed)).decode("ascii")
        except Exception:
            pass

        # solana-py legacy transaction fallback
        try:
            import base64 as _b64
            from solana.keypair import Keypair as SolanaKeypair  # type: ignore
            from solana.transaction import Transaction  # type: ignore

            secret = priv_key + SigningKey(priv_key).verify_key.encode()
            keypair = SolanaKeypair.from_secret_key(secret)
            raw = _b64.b64decode(unsigned_b64)
            tx = Transaction.deserialize(raw)
            tx.sign(keypair)
            return _b64.b64encode(bytes(tx)).decode("ascii")
        except Exception as exc:  # pragma: no cover - depends on optional deps
            raise RuntimeError(
                "Signing not available. Install 'solders' (preferred) or 'solana'. "
                f"Details: {type(exc).__name__}: {exc}"
            ) from exc

    def submit_signed_tx(self, signed_b64: str) -> str:
        """
        Submit a signed transaction (base64) via JSON-RPC ``sendTransaction``.

        Returns the transaction signature string when successful.
        """

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [signed_b64, {"encoding": "base64", "skipPreflight": False}],
        }
        resp = requests.post(self.cfg.solana_rpc_url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "result" in data:
            return data["result"]
        raise RuntimeError(f"RPC sendTransaction error: {data}")

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
