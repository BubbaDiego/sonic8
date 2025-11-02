from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

# Local IDL path (commit or drop the IDL here)
DEFAULT_IDL_PATH = Path(__file__).resolve().parents[2] / "gmsol" / "idl" / "gmsol-store.json"


async def _fetch_onchain(program_id: str, rpc_url: str) -> Optional[Dict[str, Any]]:
    """
    Try to fetch IDL from chain if anchorpy + solana-py are available.
    Safe: returns None if libs not installed.
    """
    try:
        from anchorpy import Idl
        from solana.publickey import PublicKey
        from solana.rpc.async_api import AsyncClient
    except Exception:
        return None

    client = AsyncClient(rpc_url)
    try:
        idl = await Idl.fetch(client, PublicKey(program_id))
        return idl.__dict__ if idl else None
    except Exception:
        return None
    finally:
        await client.close()


def load_local_idl(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    p = Path(path) if path else DEFAULT_IDL_PATH
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_idl(local_path: Optional[Path] = None,
             program_id: Optional[str] = None,
             rpc_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    1) Local JSON at backend/core/gmsol/idl/gmsol-store.json
    2) Else if program_id + rpc_url + anchorpy present → fetch on-chain
    """
    idl = load_local_idl(local_path)
    if idl:
        return idl

    if program_id and rpc_url:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return None
            return loop.run_until_complete(_fetch_onchain(program_id, rpc_url))
        except RuntimeError:
            return asyncio.run(_fetch_onchain(program_id, rpc_url))

    return None


def save_idl(idl: Dict[str, Any], path: Optional[Path] = None) -> Path:
    p = Path(path) if path else DEFAULT_IDL_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(idl, indent=2), encoding="utf-8")
    return p
