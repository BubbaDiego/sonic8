
import hashlib, json
from typing import Dict, Tuple, List, Any
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from .constants import PERPS_PROGRAM_ID
from .idl import _load_idl_json, _find_ix_json, _find_type_json, _camel_to_snake

try:
    from borsh_construct import U8, U64
except Exception:
    U8 = U64 = None

def _anchor_sighash(ix_name_snake: str) -> bytes:
    return hashlib.sha256(f"global:{ix_name_snake}".encode()).digest()[:8]

def _ix_name_for_hash(idl_json: dict, ix_name: str) -> str:
    ix = _find_ix_json(idl_json, ix_name)
    name = ix["name"] if ix and "name" in ix else ix_name
    return _camel_to_snake(name)

def encode_params_borsh_from_typed(idl_json: dict, defined_name: str, typed_params: Dict[str, Tuple[str, Any]]) -> bytes:
    if U8 is None or U64 is None: raise SystemExit("❌ Missing borsh-construct")
    t = _find_type_json(idl_json, defined_name)
    order = [f["name"] for f in t["type"]["fields"]] if t else list(typed_params.keys())
    out = bytearray()
    for nm in order:
        kind, val = typed_params.get(nm, ("u64", 0))
        if kind == "u64": out += U64.build(int(val))
        elif kind == "u8": out += U8.build(int(val))
        elif kind == "enum_index": out += U8.build(int(val))
        else: out += U64.build(0)
    return bytes(out)

def compute_budget_ixs() -> List[Instruction]:
    cb = Pubkey.from_string("ComputeBudget111111111111111111111111111111")
    limit_bytes = bytes([2]) + int(1_000_000).to_bytes(4,"little")
    price_bytes = bytes([3]) + int(1_000).to_bytes(8,"little")
    return [
        Instruction(program_id=cb, accounts=[], data=limit_bytes),
        Instruction(program_id=cb, accounts=[], data=price_bytes),
    ]

def build_raw_instruction(idl_path, ix_name: str, params_typed: Dict[str, Tuple[str, Any]], accounts_camel: Dict[str, Pubkey]) -> Instruction:
    j = _load_idl_json(idl_path)
    ix_json = _find_ix_json(j, ix_name)
    if not ix_json: raise SystemExit(f"❌ IDL has no ix {ix_name}")
    sig_name = _ix_name_for_hash(j, ix_name)
    sighash = _anchor_sighash(sig_name)
    arg0 = (ix_json.get("args") or [])[0]
    defined = (arg0.get("type") or {}).get("defined")
    if not defined: raise SystemExit("❌ arg0 not defined struct")
    data = sighash + encode_params_borsh_from_typed(j, defined, params_typed)
    metas: List[AccountMeta] = []
    for acc in ix_json.get("accounts", []):
        nm = acc["name"]
        cand = accounts_camel.get(nm) or accounts_camel.get(nm[0].upper()+nm[1:])
        if cand is None:
            for k,v in accounts_camel.items():
                if _camel_to_snake(k) == nm:
                    cand = v; break
        if cand is None: raise SystemExit(f"❌ Missing account '{nm}'")
        metas.append(AccountMeta(pubkey=cand, is_signer=bool(acc.get("isSigner")), is_writable=bool(acc.get("isMut"))))
    return Instruction(program_id=PERPS_PROGRAM_ID, accounts=metas, data=data)
