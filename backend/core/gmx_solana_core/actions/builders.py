from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple


def anchor_discriminator_hex(ix_name: str) -> str:
    """
    Anchor 8-byte discriminator = sha256("global:<name>")[:8].
    Kept as hex in manifest for readability.
    """
    return hashlib.sha256(f"global:{ix_name}".encode("utf-8")).digest()[:8].hex()


class IdlIndex:
    def __init__(self, idl: Dict[str, Any]):
        self.idl = idl or {}
        self._ix_map: Dict[str, Dict[str, Any]] = {}
        for ix in (self.idl.get("instructions") or []):
            if isinstance(ix, dict) and isinstance(ix.get("name"), str):
                self._ix_map[ix["name"]] = ix

    def get_ix(self, name: str) -> Optional[Dict[str, Any]]:
        return self._ix_map.get(name)


def _suggest_account_value(field_name: str, defaults: Dict[str, str]) -> Optional[str]:
    n = (field_name or "").lower()
    if n in ("authority", "owner", "user", "trader", "payer", "wallet", "signer"):
        return defaults.get("signer")
    if n in ("systemprogram", "system_program", "system"):
        return "11111111111111111111111111111111"
    if n in ("tokenprogram", "token_program", "token"):
        return "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
    if n in ("associatedtokenprogram", "associated_token_program", "ata_program"):
        return "ATokenGPvR93z8pyoAf9M1qP21wEGv6iSRxEba1r9aMJ"
    if n in ("rent",):
        return "SysvarRent111111111111111111111111111111111"
    if n in ("instructions", "sysvarinstructions", "sysvar_instructions"):
        return "Sysvar1nstructions1111111111111111111111111"
    # 'store' is a PDA account, not the program id — we leave it blank for integrator/PDA helper.
    return None


def plan_accounts(ix_def: Dict[str, Any], defaults: Dict[str, str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    accounts: List[Dict[str, Any]] = []
    missing: List[str] = []
    for a in (ix_def.get("accounts") or []):
        nm = a.get("name")
        is_mut = bool(a.get("isMut"))
        is_signer = bool(a.get("isSigner"))
        value = _suggest_account_value(nm, defaults)
        if value:
            accounts.append({"name": nm, "pubkey": value, "isWritable": is_mut, "isSigner": is_signer})
        else:
            accounts.append({"name": nm, "pubkey": "", "isWritable": is_mut, "isSigner": is_signer})
            missing.append(nm)
    return accounts, missing


def plan_args(ix_def: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for arg in (ix_def.get("args") or []):
        out.append({
            "name": arg.get("name"),
            "type": arg.get("type"),
            "value": ""  # integrator fills; types are in IDL
        })
    return out


def build_manifest(action_name: str,
                   ix_name: str,
                   program_id: str,
                   rpc_url: str,
                   signer: str,
                   idl: Dict[str, Any],
                   extra_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    idx = IdlIndex(idl)
    ix = idx.get_ix(ix_name)
    if not ix:
        raise RuntimeError(f"Instruction '{ix_name}' not found in IDL")

    accounts, missing = plan_accounts(ix, {"signer": signer})
    args = plan_args(ix)

    return {
        "action": action_name,
        "programId": program_id,
        "rpc": rpc_url,
        "instruction": ix_name,
        "anchorDiscriminatorHex": anchor_discriminator_hex(ix_name),
        "accounts": accounts,
        "args": args,
        "meta": {
            "ts": int(time.time()),
            "missing_accounts": missing,
            **(extra_meta or {})
        }
    }
