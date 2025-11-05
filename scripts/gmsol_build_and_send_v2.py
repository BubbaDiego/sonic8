# -*- coding: utf-8 -*-
"""
gmsol_build_and_send_v2.py  (mnemonic-enabled)
Build & (optionally) send GMX-Solana instructions using Anchor IDL with
solana 0.36.x / anchorpy 0.21.x / solders 0.26.x (no solana.transaction).

- Encodes instruction data via anchorpy.InstructionCoder (IDL required).
- Builds a legacy message using solders only.
- Simulates via simulateTransaction (base64), sends via sendRawTransaction.
- Signs with either:
    * --signer-json-file <keypair.json>   (Solana CLI format), or
    * --signer-mnemonic-file <signer.txt> (12/24-word seed; derives m/44'/501'/0'/0')

If --signer-mnemonic-file is used and manifest.accounts.authority is empty,
it will be auto-filled with the derived pubkey.

Usage examples omitted for brevity.
"""
from __future__ import annotations

import argparse
import base64
import hmac
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from anchorpy import Idl
from anchorpy.coder.instruction import InstructionCoder

from based58 import b58decode
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.instruction import Instruction as SInstruction, AccountMeta
from solders.hash import Hash
from solders.message import Message
from solders.transaction import VersionedTransaction

from solana.rpc.api import Client  # HTTP only


# ---------------- IDL helpers ----------------
def load_idl(path: Path) -> Idl:
    text = Path(path).read_text(encoding="utf-8")
    return Idl.from_json(text)

def _flatten_accounts(acc_items) -> List[Dict[str, Any]]:
    flat: List[Dict[str, Any]] = []
    for item in acc_items:
        if hasattr(item, "accounts") and isinstance(item.accounts, list):
            flat.extend(_flatten_accounts(item.accounts))
        else:
            flat.append({
                "name": getattr(item, "name", ""),
                "isMut": bool(getattr(item, "is_mut", False)),
                "isSigner": bool(getattr(item, "is_signer", False)),
            })
    return flat

def list_instruction_schema(idl: Idl, name: str) -> Dict[str, Any]:
    ins = next((i for i in idl.instructions if i.name == name), None)
    if ins is None:
        raise SystemExit(f"Instruction '{name}' not found in IDL.")
    accounts = _flatten_accounts(ins.accounts)
    def _type_to_str(t):
        try:
            if hasattr(t, "to_json"):
                return json.dumps(t.to_json())
            return str(t)
        except Exception:
            return str(t)
    args = []
    for a in ins.args:
        t = getattr(a, "idl_type", None)
        args.append({"name": getattr(a, "name", ""), "type": _type_to_str(t)})
    return {"instruction": name, "accounts": accounts, "args": args}


# -------------- Manifest helpers --------------
def write_skeleton_manifest(schema: Dict[str, Any], out_path: Path) -> None:
    man = {
        "instruction": schema["instruction"],
        "accounts": {a["name"]: "" for a in schema["accounts"]},
        "args": {a["name"]: None for a in schema["args"]},
        "compute_unit_price_micro_lamports": 0,
        "compute_unit_limit": 0,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(man, indent=2), encoding="utf-8")

def ensure_pubkey(s: str) -> Pubkey:
    try:
        return Pubkey.from_string(s)
    except Exception:
        try:
            Pubkey.from_bytes(b58decode(s))
            return Pubkey.from_string(s)
        except Exception:
            raise SystemExit(f"Invalid pubkey/base58: {s}")

def keypair_from_json_file(path: Path) -> Keypair:
    arr = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(arr, list):
        raise SystemExit("Keypair JSON must be an array of ints (Solana CLI format).")
    return Keypair.from_bytes(bytes(arr))


# -------------- BIP39 + SLIP-0010 (ed25519) → m/44'/501'/0'/0' --------------
BIP39_PBKDF2_ROUNDS = 2048
BIP39_SALT_PREFIX = "mnemonic"
SLIP10_KEY = b"ed25519 seed"

def _hmac_sha512(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha512).digest()

def _bip39_seed(mnemonic: str, passphrase: str = "") -> bytes:
    # PBKDF2-HMAC-SHA512(mnemonic, "mnemonic"+passphrase, 2048, 64)
    salt = (BIP39_SALT_PREFIX + passphrase).encode("utf-8")
    return hashlib.pbkdf2_hmac("sha512", mnemonic.encode("utf-8"), salt, BIP39_PBKDF2_ROUNDS, dklen=64)

def _slip10_master_key_ed25519(seed: bytes) -> tuple[bytes, bytes]:
    I = _hmac_sha512(SLIP10_KEY, seed)
    return I[:32], I[32:]  # (k, c)

def _slip10_derive_ed25519(kpar: bytes, cpar: bytes, index: int) -> tuple[bytes, bytes]:
    # Hardened only (index >= 2^31)
    data = b"\x00" + kpar + index.to_bytes(4, "big")
    I = _hmac_sha512(cpar, data)
    return I[:32], I[32:]

def _derive_m44_501_0_0(mnemonic: str, passphrase: str = "") -> bytes:
    seed = _bip39_seed(mnemonic.strip(), passphrase)
    k, c = _slip10_master_key_ed25519(seed)
    # m/44'/501'/0'/0'
    for idx in (44, 501, 0, 0):
        k, c = _slip10_derive_ed25519(k, c, idx | 0x80000000)
    return k  # 32-byte ed25519 seed

def keypair_from_mnemonic_file(path: Path, passphrase: str = "") -> Keypair:
    words = Path(path).read_text(encoding="utf-8").strip()
    # normalize whitespace & punctuation to spaces
    import re
    clean = re.sub(r"[^A-Za-z\s]", " ", words).lower().split()
    if len(clean) < 12:
        raise SystemExit(f"Mnemonic in {path} looks too short.")
    mnemonic = " ".join(clean[:24])  # supports 12..24; taking first 24 max
    seed32 = _derive_m44_501_0_0(mnemonic, passphrase)
    return Keypair.from_seed(seed32)


# -------------- build instruction (solders only) --------------
def build_ix_from_manifest(idl: Idl, program_id: Pubkey, manifest: Dict[str, Any]) -> SInstruction:
    name = manifest.get("instruction")
    if not name:
        raise SystemExit("Manifest missing 'instruction'.")

    schema = list_instruction_schema(idl, name)
    if len(schema["accounts"]) == 0 and len(schema["args"]) == 0:
        raise SystemExit(
            "IDL for this instruction has no accounts/args (likely a placeholder). "
            "Replace gmsol-store.json with the real Store IDL."
        )

    accmap = manifest.get("accounts") or {}
    missing = [a["name"] for a in schema["accounts"] if not accmap.get(a["name"])]
    if missing:
        raise SystemExit(f"Manifest missing required accounts: {missing}")

    metas: List[AccountMeta] = []
    for a in schema["accounts"]:
        pk = ensure_pubkey(accmap[a["name"]])
        metas.append(AccountMeta(pubkey=pk, is_signer=a["isSigner"], is_writable=a["isMut"]))

    argmap = manifest.get("args") or {}
    arg_values: List[Any] = []
    for a in schema["args"]:
        v = argmap.get(a["name"])
        if v is None:
            raise SystemExit(f"Manifest missing required arg '{a['name']}'")
        arg_values.append(v)

    coder = InstructionCoder(idl)
    data = coder.build(name, arg_values)
    return SInstruction(program_id=program_id, accounts=metas, data=data)


# -------------- simulate & send (raw base64) --------------
def rpc_simulate_raw(client: Client, tx_bytes: bytes) -> Dict[str, Any]:
    tx_b64 = base64.b64encode(tx_bytes).decode("utf-8")
    body = {"jsonrpc":"2.0","id":1,"method":"simulateTransaction",
            "params":[tx_b64, {"encoding":"base64","sigVerify":False,"commitment":"confirmed"}]}
    resp = client._provider.make_request(body)  # type: ignore
    if "error" in resp:
        raise SystemExit(f"simulateTransaction RPC error: {resp['error']}")
    return resp["result"]

def rpc_send_raw(client: Client, tx_bytes: bytes) -> str:
    tx_b64 = base64.b64encode(tx_bytes).decode("utf-8")
    body = {"jsonrpc":"2.0","id":1,"method":"sendRawTransaction",
            "params":[tx_b64, {"skipPreflight":False,"preflightCommitment":"confirmed"}]}
    resp = client._provider.make_request(body)  # type: ignore
    if "error" in resp:
        raise SystemExit(f"sendRawTransaction RPC error: {resp['error']}")
    return resp["result"]


# -------------- build & execute --------------
def send_or_simulate(
    rpc: str,
    program: str,
    idl_path: Path,
    manifest_path: Path,
    signer_json_file: Optional[Path],
    signer_mnemonic_file: Optional[Path],
    signer_mnemonic_passphrase: str,
    do_send: bool,
) -> None:
    client = Client(rpc)
    idl = load_idl(idl_path)
    man = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    # signer
    kp: Keypair
    if signer_json_file:
        kp = keypair_from_json_file(signer_json_file)
    elif signer_mnemonic_file:
        kp = keypair_from_mnemonic_file(signer_mnemonic_file, signer_mnemonic_passphrase)
    else:
        raise SystemExit("Provide either --signer-json-file or --signer-mnemonic-file")

    # optionally auto-fill authority if empty
    if "accounts" in man and isinstance(man["accounts"], dict):
        if not man["accounts"].get("authority"):
            man["accounts"]["authority"] = str(kp.pubkey())

    program_id = ensure_pubkey(program)
    ix = build_ix_from_manifest(idl, program_id, man)

    payer = kp.pubkey()
    bh_str = client.get_latest_blockhash().value.blockhash
    recent = Hash.from_string(bh_str)

    msg = Message.new_with_blockhash([ix], payer, recent)
    tx = VersionedTransaction(msg, [kp])
    raw = bytes(tx.serialize())

    if not do_send:
        res = rpc_simulate_raw(client, raw)
        print(json.dumps({"simulate": res}, indent=2))
        err = res.get("value", {}).get("err")
        if err:
            raise SystemExit("❌ simulate err")
        print("✅ simulation ok (no send)")
        return

    sig = rpc_send_raw(client, raw)
    print("✅ sent:", sig)
    print("🔗 https://solscan.io/tx/" + sig)


# ---------------- CLI ----------------
def main():
    ap = argparse.ArgumentParser(description="GMX-Solana: build & send (solders-only) from IDL (mnemonic/json signers).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("idl-info")
    p1.add_argument("--idl", required=True, type=Path)
    p1.add_argument("--instruction", required=True)

    p2 = sub.add_parser("make-manifest")
    p2.add_argument("--idl", required=True, type=Path)
    p2.add_argument("--instruction", required=True)
    p2.add_argument("--out", required=True, type=Path)

    p3 = sub.add_parser("send-manifest")
    p3.add_argument("--rpc", required=True)
    p3.add_argument("--program", required=True)
    p3.add_argument("--idl", required=True, type=Path)
    p3.add_argument("--manifest", required=True, type=Path)
    g = p3.add_mutually_exclusive_group(required=True)
    g.add_argument("--signer-json-file", type=Path)
    g.add_argument("--signer-mnemonic-file", type=Path)
    p3.add_argument("--signer-mnemonic-passphrase", default="", help="BIP39 passphrase (usually empty).")
    p3.add_argument("--send", action="store_true")

    args = ap.parse_args()

    if args.cmd == "idl-info":
        idl = load_idl(args.idl)
        print(json.dumps(list_instruction_schema(idl, args.instruction), indent=2))
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
            signer_mnemonic_file=args.signer_mnemonic_file,
            signer_mnemonic_passphrase=args.signer_mnemonic_passphrase,
            do_send=args.send,
        )
        return


if __name__ == "__main__":
    main()
