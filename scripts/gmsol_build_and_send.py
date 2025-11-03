# -*- coding: utf-8 -*-
"""
gmsol_build_and_send.py
Builds & (optionally) sends GMX-Solana instructions using an Anchor IDL.
- Reads instruction schema (accounts & args) strictly from your IDL JSON.
- Validates your provided accounts/args before building.
- Encodes instruction data using Anchor rules (via anchorpy).
- Signs with a Solana keypair JSON file OR a mnemonic file (if you ask for it).
- Simulates by default; add --send to broadcast.

Usage examples:
  # 1) Inspect schema
  python scripts/gmsol_build_and_send.py idl-info ^
    --idl backend\\core\\gmx_solana_core\\idl\\gmsol-store.json ^
    --instruction create_withdrawal

  # 2) Generate a skeleton manifest to fill
  python scripts/gmsol_build_and_send.py make-manifest ^
    --idl backend\\core\\gmx_solana_core\\idl\\gmsol-store.json ^
    --instruction create_withdrawal ^
    --out outbox\\create_withdrawal_skeleton.json

  # 3) Send or simulate a finalized manifest
  python scripts/gmsol_build_and_send.py send-manifest ^
    --rpc "https://mainnet.helius-rpc.com/?api-key=YOURKEY" ^
    --program Gmso1uvJnLbawvw7yezdfCDcPydwW2s2iqG3w6MDucLo ^
    --idl backend\\core\\gmx_solana_core\\idl\\gmsol-store.json ^
    --signer-json-file C:\\sonic7\\signer.json ^
    --manifest outbox\\my_filled_manifest.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Anchor + Solana (versions compatible with solana==0.32 / solders==0.20)
from anchorpy import Idl
from anchorpy.coder.instruction import InstructionCoder
from based58 import b58decode
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.rpc.types import TxOpts

from solders.instruction import Instruction as SInstruction, AccountMeta
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.message import Message
from solders.hash import Hash

# Optional compute budget helpers (solders has these helpers in many envs)
try:
    from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit
except Exception:
    set_compute_unit_price = set_compute_unit_limit = None  # graceful fallback


def load_idl(path: Path) -> Idl:
    # Anchor expects a JSON string, not a parsed dict
    text = Path(path).read_text(encoding="utf-8")
    return Idl.from_json(text)



def list_instruction_schema(idl: Idl, name: str) -> Dict[str, Any]:
    ins = next((i for i in idl.instructions if i.name == name), None)
    if ins is None:
        raise SystemExit(f"Instruction '{name}' not found in IDL.")
    accounts = [{"name": a.name, "isMut": a.is_mut, "isSigner": a.is_signer} for a in ins.accounts]
    def _idl_type_to_str(t):
        if isinstance(t, dict):
            return json.dumps(t)
        return str(t)
    args = [{"name": a.name, "type": _idl_type_to_str(a.type)} for a in ins.args]
    return {"instruction": name, "accounts": accounts, "args": args}

def write_skeleton_manifest(schema: Dict[str, Any], out_path: Path) -> None:
    man = {
        "instruction": schema["instruction"],
        "accounts": {a["name"]: "" for a in schema["accounts"]},
        "args": {a["name"]: None for a in schema["args"]},
        "compute_unit_price_micro_lamports": 0,
        "compute_unit_limit": 0
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(man, indent=2), encoding="utf-8")

def keypair_from_json_file(path: Path) -> Keypair:
    arr = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(arr, list):
        raise SystemExit("Keypair JSON must be array of ints (Solana CLI format).")
    return Keypair.from_bytes(bytes(arr))

def ensure_pubkey(s: str) -> Pubkey:
    try:
        return Pubkey.from_string(s)
    except Exception:
        try:
            Pubkey.from_bytes(b58decode(s))
            return Pubkey.from_string(s)
        except Exception:
            raise SystemExit(f"Invalid pubkey/base58: {s}")

def build_ix_from_manifest(idl: Idl, program_id: Pubkey, manifest: Dict[str, Any]) -> SInstruction:
    name = manifest.get("instruction")
    if not name:
        raise SystemExit("Manifest missing 'instruction'.")
    schema = list_instruction_schema(idl, name)

    # If the IDL has no accounts/args, you’re on a placeholder — abort early
    if len(schema["accounts"]) == 0 and len(schema["args"]) == 0:
        raise SystemExit(
            "IDL for this instruction has no accounts/args. "
            "This usually means you are using a placeholder gmsol-store.json. "
            "Replace it with the official GMX-Solana IDL."
        )

    # Validate accounts exist in manifest (and in IDL order)
    accmap = manifest.get("accounts") or {}
    missing = [a["name"] for a in schema["accounts"] if not accmap.get(a["name"])]
    if missing:
        raise SystemExit(f"Manifest missing required accounts: {missing}")

    metas: List[AccountMeta] = []
    for a in schema["accounts"]:
        pk = ensure_pubkey(accmap[a["name"]])
        metas.append(AccountMeta(pubkey=pk, is_signer=a["isSigner"], is_writable=a["isMut"]))

    # Build args **as a list** in the IDL order
    argmap = manifest.get("args") or {}
    arg_values: List[Any] = []
    for a in schema["args"]:
        v = argmap.get(a["name"])
        if v is None:
            raise SystemExit(f"Manifest missing required arg '{a['name']}'")
        arg_values.append(v)

    coder = InstructionCoder(idl)
    # Anchor coder in 0.19.x expects (name: str, args: list)
    data = coder.build(name, arg_values)

    return SInstruction(program_id=program_id, accounts=metas, data=data)


def add_compute_budget_ixs(tx: Transaction, price_micro_lamports: int, cu_limit: int) -> None:
    if set_compute_unit_price and price_micro_lamports and price_micro_lamports > 0:
        tx.add(set_compute_unit_price(price_micro_lamports))
    if set_compute_unit_limit and cu_limit and cu_limit > 0:
        tx.add(set_compute_unit_limit(cu_limit))

def send_or_simulate(
    rpc: str,
    program: str,
    idl_path: Path,
    manifest_path: Path,
    signer_json_file: Optional[Path],
    send: bool,
) -> None:
    client = Client(rpc)
    idl = load_idl(idl_path)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    program_id = ensure_pubkey(program)
    ix = build_ix_from_manifest(idl, program_id, manifest)

    # signer
    if not signer_json_file:
        raise SystemExit("Provide --signer-json-file (Solana CLI keypair JSON).")
    kp = keypair_from_json_file(signer_json_file)

    # Build v0 (legacy) tx for compatibility
    tx = Transaction()
    add_compute_budget_ixs(
        tx,
        int(manifest.get("compute_unit_price_micro_lamports", 0) or 0),
        int(manifest.get("compute_unit_limit", 0) or 0),
    )
    tx.add(ix)
    tx.fee_payer = kp.pubkey()

    # blockhash
    bh = client.get_latest_blockhash().value.blockhash
    tx.recent_blockhash = bh

    if not send:
        # simulate only
        sim = client.simulate_transaction(tx, sig_verify=False)
        print(json.dumps({"logs": sim.value.logs, "err": sim.value.err}, indent=2))
        if sim.value.err:
            raise SystemExit("❌ simulate err")
        print("✅ simulation ok (no send)")
        return

    # send
    resp = client.send_transaction(tx, kp, opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"))
    sig = resp.value
    print("✅ sent:", sig)
    print("🔗 explorer: https://solscan.io/tx/" + str(sig))


# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="GMX-Solana: build & send instructions from IDL (no guesses).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_info = sub.add_parser("idl-info", help="Show accounts & args required by an instruction.")
    ap_info.add_argument("--idl", required=True, type=Path)
    ap_info.add_argument("--instruction", required=True)

    ap_mk = sub.add_parser("make-manifest", help="Write a skeleton manifest for an instruction.")
    ap_mk.add_argument("--idl", required=True, type=Path)
    ap_mk.add_argument("--instruction", required=True)
    ap_mk.add_argument("--out", required=True, type=Path)

    ap_send = sub.add_parser("send-manifest", help="Build (+simulate or send) a manifest.")
    ap_send.add_argument("--rpc", required=True)
    ap_send.add_argument("--program", required=True)
    ap_send.add_argument("--idl", required=True, type=Path)
    ap_send.add_argument("--manifest", required=True, type=Path)
    ap_send.add_argument("--signer-json-file", required=True, type=Path,
                         help="Solana CLI keypair JSON (use solana-keygen new -o <file>.json)")
    ap_send.add_argument("--send", action="store_true", help="Actually broadcast. Default is simulate-only.")

    args = ap.parse_args()
    if args.cmd == "idl-info":
        idl = load_idl(args.idl)
        schema = list_instruction_schema(idl, args.instruction)
        print(json.dumps(schema, indent=2))
        return
    if args.cmd == "make-manifest":
        idl = load_idl(args.idl)
        schema = list_instruction_schema(idl, args.instruction)
        write_skeleton_manifest(schema, args.out)
        print(f"✅ wrote skeleton: {args.out}")
        print("→ Fill 'accounts' with Pubkeys and 'args' with values per IDL types; then use send-manifest.")
        return
    if args.cmd == "send-manifest":
        send_or_simulate(
            rpc=args.rpc,
            program=args.program,
            idl_path=args.idl,
            manifest_path=args.manifest,
            signer_json_file=args.signer_json_file,
            send=args.send,
        )
        return


if __name__ == "__main__":
    main()
