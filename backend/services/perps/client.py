from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Tuple

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from solana.rpc.async_api import AsyncClient

from backend.services.signer_loader import load_signer


RPC_URL = os.getenv("RPC_URL") or (
    f"https://mainnet.helius-rpc.com/?api-key={os.getenv('HELIUS_API_KEY')}" if os.getenv("HELIUS_API_KEY") else "https://api.mainnet-beta.solana.com"
)

IDL_DIR = Path(__file__).parent / "idl"
IDL_PERPS = IDL_DIR / "jupiter_perpetuals.json"  # <- you will vendor this JSON
IDL_DOVES = IDL_DIR / "doves.json"  # <- optional, vendor if you use it


def _read_idl(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"IDL not found at {path}. See CODΞX step to convert the TS IDL to JSON."
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


async def get_perps_program() -> Tuple[Program, AsyncClient]:
    """
    Returns an AnchorPy Program for Jupiter Perpetuals + the AsyncClient.
    Caller is responsible to `await client.close()` when done.
    """
    from anchorpy import Program, Provider, Wallet  # lazy import to avoid dependency unless needed
    idl = _read_idl(IDL_PERPS)

    # Program ID is usually inside idl["metadata"]["address"]
    try:
        program_id_str = idl["metadata"]["address"]
    except Exception:
        raise ValueError("Perps IDL JSON missing metadata.address (program id).")

    kp: Keypair = load_signer()  # uses signer.txt (your loader)
    wallet = Wallet(kp)
    client = AsyncClient(RPC_URL)
    provider = Provider(client, wallet)
    program = Program(idl, Pubkey.from_string(program_id_str), provider)
    return program, client
