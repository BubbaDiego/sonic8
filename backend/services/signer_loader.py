# backend/services/signer_loader.py
from __future__ import annotations
import json, base64, os
from typing import Optional
from solders.keypair import Keypair

DEFAULT_SIGNER_PATH = os.getenv('SONIC_SIGNER_PATH', 'signer.txt')

def load_signer(path: Optional[str] = None) -> Keypair:
    """Load a Solana Keypair from signer.txt.
    Supports:
      - Solana id.json array (64 ints)
      - Base64-encoded 64-byte secret
    """
    p = path or DEFAULT_SIGNER_PATH
    if not os.path.exists(p):
        raise FileNotFoundError(f"Signer file not found: {p}")
    raw = open(p, 'r', encoding='utf-8').read().strip()
    # Try JSON array
    try:
        arr = json.loads(raw)
        if isinstance(arr, list) and (len(arr) in (64, 32)):
            return Keypair.from_bytes(bytes(arr))
    except Exception:
        pass
    # Try base64
    try:
        b = base64.b64decode(raw)
        if len(b) in (64, 32):
            return Keypair.from_bytes(b)
    except Exception:
        pass
    raise ValueError("Unsupported signer format. Expect JSON array or base64 secret bytes.")
