# -*- coding: utf-8 -*-
"""
gmsol_build_and_send.py
Builds & (optionally) sends GMX-Solana instructions using an Anchor IDL.
- Reads instruction schema (accounts & args) strictly from your IDL JSON.
- Validates your provided accounts/args before building.
- Encodes instruction data using Anchor rules (via anchorpy).
- Signs with key from a mnemonic (signer.txt) OR a Solana keypair JSON file.
- Simulates by default; add --send to broadcast.

Usage examples:
  # 1) Inspect schema
  python scripts/gmsol_build_and_send.py idl-info ^
    --idl backend/core/gmx_solana_core/idl/gmsol-store.json ^
    --instruction create_withdrawal

  # 2) Generate a skeleton manifest to fill
  python scripts/gmsol_build_and_send.py make-manifest ^
    --idl backend/core/gmx_solana_core/idl/gmsol-store.json ^
    --instruction create_withdrawal ^
    --out outbox\create_withdrawal_skeleton.json

  # 3) Send or simulate a finalized manifest
  python scripts/gmsol_build_and_send.py send-manifest ^
    --rpc "https://mainnet.helius-rpc.com/?api-key=YOURKEY" ^
    --program Gmso1uvJnLbawvw7yezdfCDcPydwW2s2iqG3w6MDucLo ^
    --idl backend/core/gmx_solana_core/idl/gmsol-store.json ^
    --signer-mnemonic-file C:\sonic7\signer.txt ^
    --manifest outbox\my_filled_manifest.json         # add --send to broadcast
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# Anchor + Solana
from anchorpy import Idl
from anchorpy.coder.instruction import InstructionCoder
from based58 import b58decode
from solana.publickey import PublicKey
from solana.rpc.api import Client
from solana.transaction import Transaction
from solana.rpc.types import TxOpts
from solders.instruction import Instruction as SInstruction, AccountMeta
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.hash import Hash
from solders.message import Message
from solders.transaction import VersionedTransaction
from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit

# Mnemonic -> Keypair
from bip_utils import (
    Bip39MnemonicValidator,
    Bip39SeedGenerator,
    Bip44,
    Bip44Coins,
    Bip44Changes,
)
from solders.keypair import Keypair


# ---------- Utilities ----------
def load_idl(path: Path) -> Idl:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Idl.from_json(data)

def list_instruction_schema(idl: Idl, name: str) -> Dict[str, Any]:
    ins = next((i for i in idl.instructions if i.name == name), None)
    if ins is None:
        raise SystemExit(f"Instruction '{name}' not found in IDL.")
    # flatten accounts
    accounts = [{"name": a.name, "isMut": a.is_mut, "isSigner": a.is_signer} for a in ins.accounts]
    # flatten args
    def _idl_type_to_str(t):
        # render anchorpy IDL type to a readable string
        if isinstance(t, dict):
            return json.dumps(t)
        return str(t)
    args = [{"name": a.name, "type": _idl_type_to_str(a.type)} for a in ins.args]
    return {"instruction": name, "accounts": accounts, "args": args}

def write_skeleton_manifest(schema: Dict[str, Any], out_path: Path) -> None:
    # Skeleton manifest with empty strings for pubkeys and None for args
    man = {
        "instruction": schema["instruction"],
        "accounts": {a["name"]: "" for a in schema["accounts"]},
        "args": {a["name"]: None for a in schema["args"]},
        "compute_unit_price_micro_lamports": 0,
        "compute_unit_limit": 0
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(man, indent=2), encoding="utf-8")

def keypair_from_mnemonic_file(path: Path, account: int = 0, change: int = 0, index: int = 0) -> Keypair:
    words = Path(path).read_text(encoding="utf-8").strip()
    # try whole file; if file holds other text, normalize
    clean = re.sub(r"[^a-zA-Z\s]", " ", words).lower().split()
    for n in (24, 21, 18, 15, 12):
        if len(clean) >= n:
            cand = " ".join(clean[:n])
            try:
                Bip39MnemonicValidator(cand).Validate()
                seed = Bip39SeedGenerator(cand).Generate()
                ctx = Bip44.FromSeed(seed, Bip44Coins.SOLANA)
                acct = ctx.Purpose().Coin().Account(account).Change(Bip44Changes.CHAIN_EXT).AddressIndex(index)
                # Ed25519 seed (32 bytes)
                sk_bytes = acct.PrivateKey().Raw().ToBytes()  # returns 32 bytes for ed25519
                return Keypair.from_seed(sk_bytes)
            except Exception:
                continue
    raise SystemExit(f"Could not derive keypair from mnemonic file: {path}")

def keypair_from_json_file(path: Path) -> Keypair:
    arr = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(arr, list):
        raise SystemExit("Keypair JSON must be array of ints (Solana CLI format).")
    return Keypair.from_bytes(bytes(arr))

def ensure_pubkey(s: str) -> Pubkey:
    try:
        return Pubkey.from_string(s)
    except Exception:
        # allow raw base58 decode fallback to clarify errors early
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

    # Validate accounts presence
    accmap = manifest.get("accounts") or {}
    missing = [a["name"] for a in schema["accounts"] if not accmap.get(a["name"])]
    if missing:
        raise SystemExit(f"Manifest missing required accounts: {missing}")

    # Validate args presence (None means not provided)
    argmap = manifest.get("args") or {}
    arg_missing = [a["name"] for a in schema["args"] if argmap.get(a["name"]) is None]
    if arg_missing:
        raise SystemExit(f"Manifest missing required args: {arg_missing}")

    # Build account metas in IDL order
    metas: List[AccountMeta] = []
    for a in schema["accounts"]:
        pk = ensure_pubkey(accmap[a["name"]])
        metas.append(AccountMeta(pubkey=pk, is_signer=a["isSigner"], is_writable=a["isMut"]))

    # Encode data with Anchor coder
    coder = InstructionCoder(idl)
    data = coder.build(name, argmap)

    return SInstruction(
        program_id=program_id,
        accounts=metas,
        data=data
    )

def add_compute_budget_ixs(tx: Transaction, price_micro_lamports: int, cu_limit: int) -> None:
    if price_micro_lamports and price_micro_lamports > 0:
        tx.add(set_compute_unit_price(price_micro_lamports))
    if cu_limit and cu_limit > 0:
        tx.add(set_compute_unit_limit(cu_limit))

def send_or_simulate(
    rpc: str,
    program: str,
    idl_path: Path,
    manifest_path: Path,
    signer_mnemonic_file: Optional[Path],
    signer_json_file: Optional[Path],
    send: bool,
) -> None:
    client = Client(rpc)
    idl = load_idl(idl_path)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    program_id = ensure_pubkey(program)
    ix = build_ix_from_manifest(idl, program_id, manifest)

    # signer
    if signer_json_file:
        kp = keypair_from_json_file(signer_json_file)
    elif signer_mnemonic_file:
        kp = keypair_from_mnemonic_file(signer_mnemonic_file)
    else:
        raise SystemExit("Provide --signer-mnemonic-file or --signer-json-file.")

    # Build transaction (legacy for broad RPC compatibility)
    tx = Transaction()
    # Optional compute budget (from manifest)
    add_compute_budget_ixs(
        tx,
        int(manifest.get("compute_unit_price_micro_lamports", 0) or 0),
        int(manifest.get("compute_unit_limit", 0) or 0),
    )
    tx.add(ix)

    # Set payer
    tx.fee_payer = kp.pubkey()

    # Populate blockhash
    bh = client.get_latest_blockhash().value.blockhash
    tx.recent_blockhash = bh

    # Simulate first unless explicitly sending
    if not send:
        try:
            sim = client.simulate_transaction(tx, sig_verify=False)
            print(json.dumps(sim.value.logs or [], indent=2))
            err = sim.value.err
            if err:
                print("❌ simulate err:", err)
                raise SystemExit(1)
            print("✅ simulation ok (no send)")
            return
        except Exception as e:
            print("❌ simulation failed:", e)
            raise SystemExit(1)

    # Send (sign & submit)
    try:
        resp = client.send_transaction(tx, kp, opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed"))
        sig = resp.value
        print("✅ sent:", sig)
        print("🔗 explorer: https://solscan.io/tx/" + str(sig))
    except Exception as e:
        print("❌ send failed:", e)
        raise SystemExit(1)


# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="GMX-Solana: build & send instructions from IDL (no guesses).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # idl-info
    ap_info = sub.add_parser("idl-info", help="Show accounts & args required by an instruction.")
    ap_info.add_argument("--idl", required=True, type=Path)
    ap_info.add_argument("--instruction", required=True)

    # make-manifest
    ap_mk = sub.add_parser("make-manifest", help="Write a skeleton manifest for an instruction.")
    ap_mk.add_argument("--idl", required=True, type=Path)
    ap_mk.add_argument("--instruction", required=True)
    ap_mk.add_argument("--out", required=True, type=Path)

    # send-manifest
    ap_send = sub.add_parser("send-manifest", help="Build (+simulate or send) a manifest.")
    ap_send.add_argument("--rpc", required=True)
    ap_send.add_argument("--program", required=True, help="Program ID (e.g., GMX-Solana store program)")
    ap_send.add_argument("--idl", required=True, type=Path)
    ap_send.add_argument("--manifest", required=True, type=Path)
    signer = ap_send.add_mutually_exclusive_group(required=True)
    signer.add_argument("--signer-mnemonic-file", type=Path)
    signer.add_argument("--signer-json-file", type=Path, help="Solana CLI keypair JSON")
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
            signer_mnemonic_file=args.signer_mnemonic_file,
            signer_json_file=args.signer_json_file,
            send=args.send,
        )
        return


if __name__ == "__main__":
    main()
