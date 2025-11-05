# -*- coding: utf-8 -*-
"""
Fetch GMX-Solana Store IDL directly from chain via the IDL PDA.
Works with your current stack (solana==0.32 / solders).
No anchorpy.fetch() required.

Account layout (Anchor):
  [0..8)    : account discriminator (sha256("account:IdlAccount")[:8])
  [8..40)   : authority Pubkey (32 bytes)
  [40..44)  : u32 little-endian length (L) of JSON payload
  [44..44+L): IDL JSON bytes (UTF-8)

PDA:
  seeds = [b"anchor:idl", program_id.to_bytes()]
  program = program_id
"""
import base64
import json
import struct
from pathlib import Path
from solders.pubkey import Pubkey
from solana.rpc.api import Client

# === CONFIG ===
RPC = "https://mainnet.helius-rpc.com/?api-key=a8809bee-20ba-48e9-b841-0bd2bafd60b9"
PROGRAM_ID = Pubkey.from_string("Gmso1uvJnLbawvw7yezdfCDcPydwW2s2iqG3w6MDucLo")
OUT = Path(r"C:\sonic7\backend\core\gmx_solana_core\idl\gmsol-store.json")


def find_idl_pda(program_id: Pubkey) -> Pubkey:
    # Anchor derives IDL PDA with seeds [b"anchor:idl", program_id]
    seeds = [b"anchor:idl", bytes(program_id)]
    pda, _ = Pubkey.find_program_address(seeds, program_id)
    return pda


def main():
    client = Client(RPC)
    idl_pda = find_idl_pda(PROGRAM_ID)

    resp = client.get_account_info(idl_pda, encoding="base64")
    val = resp.value
    if val is None:
        raise SystemExit(f"IDL PDA account not found: {idl_pda}")

    data_field = val.data
    if isinstance(data_field, list):
        data_b64 = data_field[0]
    elif isinstance(data_field, str):
        data_b64 = data_field
    else:
        raise SystemExit("Unexpected account data format")

    raw = base64.b64decode(data_b64)

    if len(raw) < 44:
        raise SystemExit("IDL account too small to contain header + length")

    # Skip discriminator (8) + authority (32)
    # Next 4 bytes (LE) is the length of the JSON payload
    json_len = struct.unpack_from("<I", raw, 40)[0]
    start = 44
    end = start + json_len
    if end > len(raw):
        raise SystemExit(f"IDL length {json_len} exceeds account data size {len(raw)}")

    idl_json_bytes = raw[start:end]
    # Sanity parse as JSON to verify well-formed
    try:
        parsed = json.loads(idl_json_bytes.decode("utf-8"))
    except Exception as e:
        raise SystemExit(f"IDL JSON parse failed: {e}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
    print("✅ Saved:", OUT)
    print("   PDA:", str(idl_pda))


if __name__ == "__main__":
    main()
