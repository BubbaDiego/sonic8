from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Tuple

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from solana.rpc.async_api import AsyncClient
from anchorpy import Program, Provider, Wallet, Idl

from backend.services.signer_loader import load_signer


RPC_URL = os.getenv("RPC_URL") or (
    f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}"
    if os.getenv("HELIUS_API_KEY")
    else "https://api.mainnet-beta.solana.com"
)

IDL_DIR = Path(__file__).parent / "idl"
IDL_PERPS = IDL_DIR / "jupiter_perpetuals.json"  # vendor JSON here
IDL_DOVES = IDL_DIR / "doves.json"  # optional


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"IDL not found at {path}. Convert TS → JSON and place it here."
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _program_id_from_idl_json(idl_json: dict) -> str:
    meta = idl_json.get("metadata") or {}
    addr = meta.get("address") or os.getenv("PERPS_PROGRAM_ID", "").strip()
    if not addr:
        raise ValueError(
            "Perps IDL missing metadata.address and PERPS_PROGRAM_ID not set."
        )
    return addr


async def get_perps_program() -> Tuple[Program, AsyncClient]:
    idl_json = _read_json(IDL_PERPS)
    idl = Idl.from_json(idl_json)
    program_id = Pubkey.from_string(_program_id_from_idl_json(idl_json))

    kp: Keypair = load_signer()
    wallet = Wallet(kp)
    client = AsyncClient(RPC_URL)
    provider = Provider(client, wallet)
    program = Program(idl, program_id, provider)
    return program, client
