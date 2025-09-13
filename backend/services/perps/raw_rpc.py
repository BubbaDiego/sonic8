from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests


# ---------- RPC URL ----------
def _rpc_url() -> str:
    env_rpc = (os.getenv("RPC_URL") or "").strip()
    if env_rpc:
        return env_rpc
    helius = (os.getenv("HELIUS_API_KEY") or "").strip()
    if helius:
        return f"https://mainnet.helius-rpc.com/?api-key={helius}"
    return "https://api.mainnet-beta.solana.com"


RPC_URL = _rpc_url()

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


# ---------- raw JSON-RPC ----------
def _rpc(method: str, params: Any) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    r = requests.post(RPC_URL, json=payload, timeout=25)
    r.raise_for_status()
    data = r.json()
    if "error" in data and data["error"]:
        raise RuntimeError(f"RPC error: {data['error']}")
    return data.get("result")
