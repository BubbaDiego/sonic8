"""Utilities for working with Solana base58 public keys."""
from __future__ import annotations

import re
from typing import Iterable

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_SET = set(BASE58_ALPHABET)
BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]+$")
BASE58_FIND = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,}")


def iter_base58_tokens(value: str) -> Iterable[str]:
    """Yield base58-looking substrings in the order they appear."""
    if not value:
        return
    for match in BASE58_FIND.finditer(value):
        yield match.group(0)


def extract_pubkey(value: str) -> str:
    """Best effort extraction of a base58 pubkey from noisy strings."""
    if not value:
        return ""

    value = str(value).strip()
    lowered = value.lower()

    if lowered.startswith("solana:"):
        cleaned = value.split(":", 1)[1]
        return cleaned.split("?", 1)[0]

    match = re.search(r"address/([1-9A-HJ-NP-Za-km-z]+)", value)
    if match:
        return match.group(1)

    leading = re.split(r"[?#\s]", value)[0]
    if BASE58_RE.fullmatch(leading or ""):
        return leading

    for token in iter_base58_tokens(value):
        return token

    return ""


def is_base58_pubkey(value: str) -> bool:
    """Return True if *value* looks like a Solana base58 pubkey."""
    return bool(value) and BASE58_RE.fullmatch(value) and len(value) >= 32
