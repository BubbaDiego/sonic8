# backend/services/perps/client.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Tuple

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from solana.rpc.async_api import AsyncClient
from anchorpy import Program, Provider, Wallet, Idl  # <-- Idl is key

from backend.services.signer_loader import load_signer


RPC_URL = os.getenv("RPC_URL") or (
    f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}"
    if os.getenv("HELIUS_API_KEY") else
    "https://api.mainnet-beta.solana.com"
)

IDL_DIR = Path(__file__).parent / "idl"
IDL_PERPS = IDL_DIR / "jupiter_perpetuals.json"   # vendor this JSON
IDL_DOVES = IDL_DIR / "doves.json"                # optional


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"IDL not found at {path}.\n"
            "Convert the TS IDL to JSON and place it here (see CODΞX step)."
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _program_id_from_idl_json(idl_json: dict) -> str:
    # common place in Anchor IDLs produced from TS:
    # idl_json["metadata"]["address"] -> program pubkey
    meta = idl_json.get("metadata") or {}
    addr = meta.get("address")
    if not addr:
        # allow override via env if not present
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

    # Convert dict -> Idl dataclass (fix for: 'dict' has no attribute 'instructions')
    idl = Idl.from_json(idl_json)

    program_id_str = _program_id_from_idl_json(idl_json)
    program_id = Pubkey.from_string(program_id_str)

    kp: Keypair = load_signer()
    wallet = Wallet(kp)
    client = AsyncClient(RPC_URL)
    provider = Provider(client, wallet)

    program = Program(idl, program_id, provider)
    return program, client
