# backend/services/perps/client.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Tuple

from anchorpy import Idl, Program, Provider, Wallet
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey

from backend.config.rpc import helius_url
from backend.services.signer_loader import load_signer


# ---------- RPC URL ----------


def _rpc_url() -> str:
    override = os.getenv("RPC_URL")
    if override:
        return override
    return helius_url()


RPC_URL = _rpc_url()

# ---------- IDL paths ----------
IDL_DIR = Path(__file__).parent / "idl"
IDL_PERPS = IDL_DIR / "jupiter_perpetuals.json"   # <- vendor JSON here
IDL_DOVES = IDL_DIR / "doves.json"                # <- optional


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"IDL not found at {path}.\n"
            "Convert the TS IDL to JSON and place it here."
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _program_id_from_idl_json(idl_json: dict) -> str:
    # most Anchor IDLs expose it at metadata.address
    meta = idl_json.get("metadata") or {}
    addr = (meta.get("address") or "").strip()
    if not addr:
        # allow env override
        addr = os.getenv("PERPS_PROGRAM_ID", "").strip()
    if not addr:
        raise ValueError("Perps IDL missing metadata.address and PERPS_PROGRAM_ID not set.")
    return addr


async def get_perps_program() -> Tuple[Program, AsyncClient]:
    """
    Build an AnchorPy Program for Jupiter Perpetuals and return (program, client).
    Caller must `await client.close()` when done.
    """
    idl_json = _read_json(IDL_PERPS)
    idl = Idl.from_json(idl_json)                       # convert dict -> Idl (fixes .instructions errors)
    program_id = Pubkey.from_string(_program_id_from_idl_json(idl_json))

    kp: Keypair = load_signer()
    wallet = Wallet(kp)
    client = AsyncClient(RPC_URL)
    provider = Provider(client, wallet)
    program = Program(idl, program_id, provider)
    return program, client
