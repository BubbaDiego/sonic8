from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from backend.services.solana_rpc import rpc_post


# ---------- Program ID (from IDL or env) ----------
IDL_DIR = Path(__file__).parent / "idl"
IDL_PERPS = IDL_DIR / "jupiter_perpetuals.json"


def get_program_id() -> str:
    # try env override first
    pid = (os.getenv("PERPS_PROGRAM_ID") or "").strip()
    if pid:
        return pid

    if not IDL_PERPS.exists():
        raise FileNotFoundError(
            f"IDL not found at {IDL_PERPS}. "
            "Either set PERPS_PROGRAM_ID env var or place a canonical Anchor JSON IDL there."
        )
    idl = json.loads(IDL_PERPS.read_text(encoding="utf-8"))
    meta = idl.get("metadata") or {}
    addr = (meta.get("address") or "").strip()
    if not addr:
        raise ValueError(
            "Perps IDL missing metadata.address; set PERPS_PROGRAM_ID in env to proceed."
        )
    return addr


def get_idl_account_names() -> List[str]:
    names: List[str] = []
    try:
        idl = json.loads(IDL_PERPS.read_text(encoding="utf-8"))
        for acc in idl.get("accounts") or []:
            n = acc.get("name")
            if isinstance(n, str):
                names.append(n)
    except Exception:
        pass
    return names


# ---------- raw JSON-RPC (compat shim) ----------
def _rpc(method: str, params: Any) -> Any:
    return rpc_post(method, params)
