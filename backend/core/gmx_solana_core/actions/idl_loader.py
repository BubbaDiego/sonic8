from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

# ✅ Default local IDL path under gmx_solana_core
DEFAULT_IDL_PATH = Path(__file__).resolve().parents[1] / "idl" / "gmsol-store.json"


def _json_idl_path_override() -> Optional[Path]:
    """
    If the console JSON specifies an 'idl_path', use that instead.
    C:\\sonic7\\gmx_solana_console.json → {"idl_path":"C:\\sonic7\\backend\\core\\gmx_solana_core\\idl\\gmsol-store.json"}
    """
    cfg = Path(r"C:\\sonic7\\gmx_solana_console.json")
    if not cfg.exists():
        return None
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
        p = data.get("idl_path")
        return Path(p) if p else None
    except Exception:
        return None


async def _fetch_onchain(program_id: str, rpc_url: str) -> Optional[Dict[str, Any]]:
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
    # JSON override takes precedence
    override = _json_idl_path_override()
    p = override or (Path(path) if path else DEFAULT_IDL_PATH)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_idl(local_path: Optional[Path] = None,
             program_id: Optional[str] = None,
             rpc_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
    # honor override on save as well
    p = _json_idl_path_override() or (Path(path) if path else DEFAULT_IDL_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(idl, indent=2), encoding="utf-8")
    return p
