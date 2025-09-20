from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Literal, Optional, Tuple

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from backend.services.perps.markets import resolve_market, resolve_extra_account
from backend.services.solana_rpc import rpc_post as rpc

CU_LIMIT = int(os.getenv("PERPS_CU_LIMIT", 800_000))
CU_PRICE = int(os.getenv("PERPS_CU_PRICE", 100_000))  # micro-lamports per CU
USD_SCALE = int(os.getenv("PERPS_USD_SCALE", 1_000_000))

SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
SPL_TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROG = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
EXPECTED_POSITION_PDA = Pubkey.from_string("7fpqAhNYnRegBsWDfoSNSLD6aDMXLQHzuruABfpnxYVv")

IDL_PATH = os.path.join(os.path.dirname(__file__), "idl", "jupiter_perpetuals.json")

DEFAULT_BASE_MINT = "So11111111111111111111111111111111111111112"
DEFAULT_QUOTE_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
DEFAULT_ORACLE_PUBKEY = "11111111111111111111111111111111"
def recent_blockhash() -> Hash:
    result = rpc("getLatestBlockhash", [{"commitment": "finalized"}])
    return Hash.from_string(result["value"]["blockhash"])


def load_signer() -> Keypair:
    from backend.services.signer_loader import load_signer as _load

    return _load()


def load_idl() -> Dict[str, Any]:
    with open(IDL_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def program_id_from_idl(idl: Dict[str, Any]) -> Pubkey:
    address = idl.get("metadata", {}).get("address") or idl.get("address")
    if not address:
        raise RuntimeError("Perps IDL missing program address (metadata.address/address).")
    return Pubkey.from_string(address)


def _idl_ix_map(idl: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    instructions = idl.get("instructions") or []
    return {str(ix.get("name", "")).lower(): ix for ix in instructions}


def _find_ix_any(idl: Dict[str, Any], candidates: List[str], fallback_any: List[str]) -> Dict[str, Any]:
    """
    Pick the correct IDL instruction robustly:
      1) exact (case-insensitive) name match
      2) substring match (in the order provided)
      3) heuristic "all tokens present"
    Fails clearly with the list of available names.
    """

    ix_map = _idl_ix_map(idl)
    names = {k.lower(): ix_map[k] for k in ix_map}

    # 1) exact, case-insensitive
    for cand in candidates:
        c = cand.lower()
        if c in names:
            return names[c]

    # 2) ordered substring
    for cand in candidates:
        c = cand.lower()
        for name, ix in names.items():
            if c in name:
                return ix

    # 3) all fallback tokens must appear
    tokens = [t.lower() for t in fallback_any if t]
    if tokens:
        for name, ix in names.items():
            if all(t in name for t in tokens):
                return ix

    have = sorted(names.keys())
    raise RuntimeError(f"Instruction not found; tried {candidates} / {fallback_any}. IDL has: {have}")


_PK_RE = re.compile(r"([1-9A-HJ-NP-Za-km-z]{32,})")


# --- begin: helpers for PDA adoption and unknown-account resolution ---

_B58 = r"[1-9A-HJ-NP-Za-km-z]{32,44}"


def _derive_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    from backend.perps.pdas import derive_ata as _impl

    return _impl(owner, mint)


def _parse_anchor_right_pda(logs: List[str]) -> Optional[str]:
    """
    Looks for:
      AnchorError caused by account: position_request. Error Code: ConstraintSeeds ...
      ...
      Right:
      <PDA>
    Returns the right-hand expected PDA (base58 string) if found.
    """

    right_idx = None
    for i, line in enumerate(logs):
        if line.strip().endswith("Right:") or line.strip().endswith("Right:"):
            right_idx = i
            break
    if right_idx is None:
        # Some chains prefix with 'Program log: Right:'
        for i, line in enumerate(logs):
            if "Right:" in line:
                right_idx = i
                break
    if right_idx is not None:
        # find next non-empty line with a base58 pubkey
        for j in range(right_idx + 1, min(right_idx + 5, len(logs))):
            m = re.search(_B58, logs[j].strip())
            if m:
                return m.group(0)
    return None


def _parse_anchor_constraint_seeds(logs: List[str]) -> Optional[Tuple[str, str]]:
    """
    Return (account_name, right_pubkey_b58) for Anchor 'ConstraintSeeds' blocks, e.g.

      AnchorError caused by account: position_request. Error Code: ConstraintSeeds ...
      ...
      Right:
      <PDA>

    If we can't parse both pieces, return None.
    """

    acct = None
    right = None

    for i, line in enumerate(logs):
        if "caused by account:" in line:
            m = re.search(r"caused by account:\s*([A-Za-z0-9_]+)", line)
            if m:
                acct = m.group(1).strip()
                # Scan forward for the Right: pubkey
                for j in range(i, min(i + 8, len(logs))):
                    if "Right:" in logs[j]:
                        for k in range(j + 1, min(j + 5, len(logs))):
                            m2 = re.search(_B58, logs[k].strip())
                            if m2:
                                right = m2.group(0)
                                return (acct, right)
                break
    return None


def _parse_unknown_account(logs: List[str]) -> Optional[str]:
    """
    Looks for: 'Instruction references an unknown account <PUBKEY>'
    Returns the unknown pubkey if present.
    """

    rx = re.compile(r"Instruction references an unknown account\s+(%s)" % _B58)
    for line in logs:
        m = rx.search(line)
        if m:
            return m.group(1)
    return None


def _parse_invalid_collateral(logs: List[str]) -> Optional[Tuple[str, str]]:
    """
    Looks for Jupiter Perps 'InvalidCollateralAccount' diagnostic block:
      ...
      Error Code: InvalidCollateralAccount ...
      Left:
      <base custody pk>
      Right:
      <collateral custody pk>
    Returns (left, right) if found.
    """

    saw = False
    left: Optional[str] = None
    right: Optional[str] = None
    for i, line in enumerate(logs):
        if "InvalidCollateralAccount" in line or "Invalid collateral account" in line:
            saw = True
        if saw and "Left:" in line and left is None:
            m = re.search(_B58, " ".join(logs[i : i + 3]))
            if m:
                left = m.group(0)
        if saw and "Right:" in line and right is None:
            m = re.search(_B58, " ".join(logs[i : i + 3]))
            if m:
                right = m.group(0)
        if saw and left and right:
            return left, right
    return None


def _saw_writable_privilege_escalated(logs: List[str]) -> bool:
    return any("writable privilege escalated" in line for line in logs)


def _saw_unauthorized_signer_or_writable(logs: List[str]) -> bool:
    return any("Cross-program invocation with unauthorized signer or writable account" in line for line in logs)


def _is_invalid_program_id_for_token_program(logs: List[str]) -> bool:
    # Prevent regressions where 'unknown' was inserted into metas[11] and displaced token program
    return any(
        "Error Code: InvalidProgramId" in line and "token_program" in logs[idx - 1 : idx + 3]
        for idx, line in enumerate(logs)
    )


def _rebuild_after_request_adopt(account_mapping: dict, request_pda_b58: str, input_mint: "Pubkey") -> None:
    """
    Replace positionRequest + recompute its ATA (owned by the adopted PDA).
    """

    request_pk = Pubkey.from_string(request_pda_b58)
    account_mapping["positionRequest"] = request_pk
    account_mapping["position_request"] = request_pk

    # Re-derive ATA for the *request PDA* (not the wallet owner)
    try:
        request_ata = _derive_ata(request_pk, input_mint)
        account_mapping["positionRequestAta"] = request_ata
        account_mapping["position_request_ata"] = request_ata
        print(f"[perps] rebuilt positionRequestAta for adopted request → {str(request_ata)}")
    except Exception as e:
        # Safe fallback: leave previous ATA if derive fails (but we loudly log it)
        print(f"[perps] WARN: failed to derive ATA for adopted request {request_pda_b58}: {e}")


def _append_remaining_account(remaining: list, pk_b58: str, signer: bool = False, writable: bool = False) -> None:
    """
    Add once if not already present. Keeps order stable and never touches required accounts.
    """

    pk = Pubkey.from_string(pk_b58)
    for acc in remaining:
        if acc["pubkey"] == pk:
            # already present; update flags if needed
            acc["is_signer"] = acc.get("is_signer", False) or signer
            acc["is_writable"] = acc.get("is_writable", False) or writable
            return
    remaining.append(
        {
            "pubkey": pk,
            "is_signer": signer,
            "is_writable": writable,
            "name": None,  # unknown / dynamic
        }
    )
    print(f"[perps] remaining_accounts += {pk_b58} (signer={signer}, writable={writable})")


# --- end: helpers for PDA adoption and unknown-account resolution ---


# ── Sim/Log Helpers ──────────────────────────────────────────────────────────
def _print_idl_accounts_audit(ix_idl: dict, mapping: dict):
    """
    Print an audit of each IDL-declared account in order:
      [idx] <name> required/optional ⇒ provided=<bool> pk=<pubkey or '-'>
    """

    accs = ix_idl.get("accounts") or []
    print("[perps] === IDL ACCOUNTS AUDIT ===")
    for i, acc in enumerate(accs):
        nm = acc.get("name")
        opt = bool(acc.get("isOptional"))
        pk = mapping.get(nm)
        is_signer = bool(acc.get("isSigner"))
        is_mut = bool(acc.get("isMut"))
        print(
            f"  [{i:02d}] {nm:24s} required={not opt:<5} ⇒ provided={pk is not None:<5} "
            f"signer={is_signer:<5} writable={is_mut:<5} pk={str(pk) if pk else '-'}"
        )


def _print_remaining_accounts(metas: list, ix_idl: dict):
    """
    Print any metas beyond the IDL-declared accounts as 'remaining accounts'.
    """

    decl = len(ix_idl.get("accounts") or [])
    if len(metas) <= decl:
        print("[perps] remaining_accounts: none")
        return
    print("[perps] === REMAINING ACCOUNTS (appended) ===")
    for i in range(decl, len(metas)):
        m = metas[i]
        print(f"  [+{i-decl:02d}] pk={m.pubkey} signer={m.is_signer} writable={m.is_writable}")


def _disc_from_idl(ix_idl: Dict[str, Any]) -> bytes:
    """
    Prefer discriminator embedded in the IDL. If absent, derive the Anchor sighash
    using a *deterministic snake_case* of the instruction name, with a special-case
    fix for Jupiter Perps' "createIncreasePositionMarketRequest".
    """

    disc = ix_idl.get("discriminant") or ix_idl.get("discriminator")
    # Newer Anchor: {"discriminant":{"bytes":[..8..]}} or {"discriminant":{"value":[..8..]}}
    if isinstance(disc, dict):
        arr = disc.get("bytes") or disc.get("value")
        if isinstance(arr, list) and len(arr) == 8:
            return bytes(int(x) & 0xFF for x in arr)
    # Very old Anchor: {"discriminator":[..8..]}
    if isinstance(disc, list) and len(disc) == 8:
        return bytes(int(x) & 0xFF for x in disc)

    raw_name = str(ix_idl.get("name", "")).strip()
    n = raw_name.lower()
    # 🔒 harden: if this looks like the perps "createIncreasePositionMarketRequest", enforce the canonical snake
    if "increase" in n and "position" in n and "request" in n and "market" in n:
        canon = "create_increase_position_market_request"
        return hashlib.sha256(f"global:{canon}".encode("utf-8")).digest()[:8]

    # generic snake_case fallback
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw_name).lower()
    s = re.sub(r"[^a-z0-9_]", "_", s)
    return hashlib.sha256(f"global:{s}".encode("utf-8")).digest()[:8]


def _types_index(idl: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for entry in idl.get("types") or []:
        name = str(entry.get("name", ""))
        if name:
            out[name] = entry.get("type") or {}
    return out


def _is_pk_like(kind: Any) -> bool:
    if kind == "publicKey":
        return True
    if isinstance(kind, dict) and "option" in kind:
        return _is_pk_like(kind["option"])
    if isinstance(kind, dict) and "defined" in kind:
        return "pubkey" in str(kind["defined"]).lower()
    return False


def _enc_scalar(kind: Any, value: Any) -> bytes:
    if kind == "bool":
        return (1 if bool(value) else 0).to_bytes(1, "little")
    if kind == "u8":
        return int(value).to_bytes(1, "little", signed=False)
    if kind == "u16":
        return int(value).to_bytes(2, "little", signed=False)
    if kind == "u32":
        return int(value).to_bytes(4, "little", signed=False)
    if kind == "i32":
        return int(value).to_bytes(4, "little", signed=True)
    if kind == "u64":
        return int(value).to_bytes(8, "little", signed=False)
    if kind == "i64":
        return int(value).to_bytes(8, "little", signed=True)
    if kind == "u128":
        return int(value).to_bytes(16, "little", signed=False)
    if kind == "i128":
        return int(value).to_bytes(16, "little", signed=True)
    if kind == "publicKey":
        return bytes(Pubkey.from_string(value))
    raise RuntimeError(f"Unmapped scalar type: {kind}")


def _enc_value(kind: Any, value: Any, types: Dict[str, Dict[str, Any]]) -> bytes:
    if isinstance(kind, dict) and "option" in kind:
        inner = kind["option"]
        if value in (None, "", 0, False):
            return b"\x00"
        return b"\x01" + _enc_value(inner, value, types)

    if isinstance(kind, dict) and "defined" in kind:
        name = str(kind["defined"])
        defined = types.get(name) or {}
        k = defined.get("kind")
        if k == "struct":
            result = bytearray()
            fields: List[Dict[str, Any]] = defined.get("fields") or []
            src = value if isinstance(value, dict) else {}
            for field in fields:
                fname = field["name"]
                fkind = field["type"]
                fvalue = src.get(fname)
                if fvalue is None:
                    if _is_pk_like(fkind):
                        fvalue = (
                            src.get("owner")
                            or src.get("authority")
                            or src.get("trader")
                            or src.get("user")
                        )
                    if fvalue is None:
                        fvalue = 0
                result += _enc_value(fkind, fvalue, types)
            return bytes(result)
        if k == "enum":
            variants: List[Dict[str, Any]] = defined.get("variants") or []
            tag: int
            payload = b""
            if isinstance(value, str):
                names = [variant.get("name") for variant in variants]
                if value not in names:
                    raise RuntimeError(f"Enum '{name}' variant '{value}' not found")
                tag = names.index(value)
                variant = variants[tag]
                fields = variant.get("fields") or []
                if fields:
                    raise RuntimeError(
                        f"Enum '{name}' variant '{value}' requires payload values"
                    )
            elif isinstance(value, dict):
                if not value:
                    raise RuntimeError(f"Enum '{name}' requires variant selection")
                variant_name = next(iter(value.keys()))
                tag = next(
                    idx
                    for idx, variant in enumerate(variants)
                    if variant.get("name") == variant_name
                )
                variant = variants[tag]
                fields = variant.get("fields") or []
                if fields:
                    variant_value = value.get(variant_name)
                    if variant_value is None:
                        raise RuntimeError(
                            f"Enum '{name}' variant '{variant_name}' requires payload values"
                        )
                    payload_bytes = bytearray()
                    for idx, field in enumerate(fields):
                        field_kind: Any
                        field_name: Optional[str] = None
                        field_kind = field
                        if isinstance(field, dict):
                            field_name = field.get("name")
                            field_kind = field.get("type")
                        if field_kind is None:
                            raise RuntimeError(
                                f"Enum '{name}' variant '{variant_name}' has field with no type"
                            )

                        field_value: Any = None
                        if isinstance(variant_value, dict) and field_name:
                            if field_name in variant_value:
                                field_value = variant_value[field_name]

                        if field_value is None:
                            if isinstance(variant_value, (list, tuple)):
                                if idx < len(variant_value):
                                    field_value = variant_value[idx]
                            elif len(fields) == 1 and not isinstance(variant_value, dict):
                                field_value = variant_value

                        if field_value is None:
                            if isinstance(field_kind, dict) and "option" in field_kind:
                                field_value = None
                            elif _is_pk_like(field_kind):
                                src = variant_value if isinstance(variant_value, dict) else {}
                                if isinstance(src, dict):
                                    field_value = (
                                        src.get("owner")
                                        or src.get("authority")
                                        or src.get("trader")
                                        or src.get("user")
                                    )
                            if field_value is None:
                                field_value = 0

                        payload_bytes += _enc_value(field_kind, field_value, types)
                    payload = bytes(payload_bytes)
            else:
                raise RuntimeError(f"Enum '{name}' requires str or dict value")
            return tag.to_bytes(1, "little") + payload
        if "pubkey" in str(defined).lower():
            return _enc_scalar("publicKey", value)
        return b"\x00"

    return _enc_scalar(kind, value)


def enc_arg(kind: Any, value: Any, types: Dict[str, Dict[str, Any]]) -> bytes:
    return _enc_value(kind, value, types)


def build_data(
    ix_idl: Dict[str, Any],
    arg_values: Dict[str, Any],
    idl_types: Dict[str, Dict[str, Any]],
) -> bytes:
    data = bytearray()
    disc = _disc_from_idl(ix_idl)
    try:
        used = ix_idl.get("name", "?")
        print(f"[perps] using ix='{used}' disc=0x{binascii.hexlify(disc).decode()}")
    except Exception:
        pass
    data += disc
    for arg in ix_idl.get("args", []):
        name = arg["name"]
        if name not in arg_values:
            raise RuntimeError(f"Missing required arg '{name}' for instruction '{ix_idl['name']}'")
        type_def = arg["type"]
        data += enc_arg(type_def, arg_values[name], idl_types)
    return bytes(data)


def compute_budget_ixs() -> List[Instruction]:
    return [set_compute_unit_limit(CU_LIMIT), set_compute_unit_price(CU_PRICE)]


def _pubkey_from_str(value: str, market: str, name: str) -> Pubkey:
    if not value:
        raise RuntimeError(f"Missing mapping for '{name}' on market '{market}'")
    if "ReplaceWith" in value:
        raise RuntimeError(
            f"Account '{name}' for market '{market}' is still a placeholder ({value}). Update the registry."
        )
    return Pubkey.from_string(value)


def map_accounts(
    ix_idl: Dict[str, Any],
    owner: Pubkey,
    position: Pubkey,
    request: Pubkey,
    base_accounts: Dict[str, str],
    market: str,
    resolve_extra,
    program_id: Pubkey,
    input_mint: Optional[Pubkey],
) -> Tuple[List[AccountMeta], Dict[str, Pubkey]]:
    from backend.perps.pdas import derive_ata, derive_event_authority, derive_perpetuals_pda

    metas: List[AccountMeta] = []
    mapping: Dict[str, Pubkey] = {}
    referral_env = os.getenv("JUP_PERPS_REFERRAL", "").strip()
    referral_default = Pubkey.from_string(referral_env or str(owner))
    custody_base = base_accounts.get("custody") or base_accounts.get("custody_base")
    collateral_value = (
        base_accounts.get("collateralCustody")
        or base_accounts.get("collateral_custody")
        or base_accounts.get("custody_quote")
    )

    for acc in ix_idl.get("accounts", []):
        name = acc["name"]
        is_signer = bool(acc.get("isSigner"))
        is_writable = bool(acc.get("isMut"))

        if name in ("owner", "user", "trader"):
            mapping[name] = owner
        elif name in ("position",):
            mapping[name] = position
        elif name in ("positionRequest", "position_request"):
            mapping[name] = request
        elif name in ("pool",):
            mapping[name] = _pubkey_from_str(base_accounts["pool"], market, "pool")
        elif name in ("priceOracle", "oracle") and "oracle" in base_accounts:
            mapping[name] = _pubkey_from_str(base_accounts["oracle"], market, "oracle")
        elif name in ("custody", "baseCustody", "base_custody"):
            if not custody_base:
                raise RuntimeError(f"custody mapping missing for market '{market}'")
            mapping[name] = _pubkey_from_str(custody_base, market, "custody")
        elif name in ("collateralCustody", "collateral_custody"):
            if not collateral_value:
                raise RuntimeError(f"collateralCustody mapping missing for market '{market}'")
            mapping[name] = _pubkey_from_str(collateral_value, market, "collateralCustody")
        elif name in (
            "custodyDovesPriceAccount",
            "custodyPythnetPriceAccount",
            "collateralCustodyDovesPriceAccount",
            "collateralCustodyPythnetPriceAccount",
            "collateralCustodyTokenAccount",
        ):
            key = name
            if key not in base_accounts:
                mapping[name] = _pubkey_from_str(resolve_extra(market, key), market, key)
            else:
                mapping[name] = _pubkey_from_str(base_accounts[key], market, key)
        elif name in (
            "referral",
            "referrer",
            "referralAccount",
            "referrerAccount",
            "refAccount",
            "ref",
        ):
            mapping[name] = referral_default
        elif name in ("tokenProgram", "token_program"):
            # Canonical: SPL Token program goes in tokenProgram slot.
            mapping[name] = SPL_TOKEN_PROGRAM
        elif name in ("systemProgram", "system_program"):
            mapping[name] = SYSTEM_PROGRAM
        elif name in (
            "associatedTokenProgram",
            "associated_token_program",
            "ataProgram",
            "ata_program",
        ):
            mapping[name] = ASSOCIATED_TOKEN_PROG
        elif name in ("perpetuals",):
            mapping[name] = derive_perpetuals_pda()
        elif name in (
            "eventAuthority",
            "event_authority",
            "eventAuthorityPda",
            "__event_authority",
        ):
            mapping[name] = derive_event_authority()
        elif name in ("program",):
            mapping[name] = program_id
        elif name in ("fundingAccount", "receivingAccount"):
            if input_mint is None:
                mint_value = base_accounts.get("input_mint")
                if mint_value:
                    input_mint = _pubkey_from_str(mint_value, market, "input_mint")
            if input_mint is None:
                raise RuntimeError("input mint not configured for funding/receiving account derivation")
            owner_for_ata = owner
            mapping[name] = derive_ata(owner_for_ata, input_mint)
        elif name in ("positionRequestAta", "position_request_ata"):
            if input_mint is None:
                mint_value = base_accounts.get("input_mint")
                if mint_value:
                    input_mint = _pubkey_from_str(mint_value, market, "input_mint")
            if input_mint is None:
                raise RuntimeError("input mint not configured for position request ATA derivation")
            mapping[name] = derive_ata(request, input_mint)
        elif name in ("inputMint", "input_mint"):
            mint_value = base_accounts.get("input_mint")
            if mint_value:
                mapping[name] = _pubkey_from_str(mint_value, market, "input_mint")
            else:
                mapping[name] = _pubkey_from_str(resolve_extra(market, name), market, name)
        else:
            value = resolve_extra(market, name)
            mapping[name] = _pubkey_from_str(value, market, name)

        if name in mapping:
            metas.append(AccountMeta(mapping[name], is_signer, is_writable))
        elif not acc.get("isOptional"):
            raise RuntimeError(f"Missing account mapping for '{name}' in '{ix_idl['name']}'")

    return metas, mapping


def _market_info(market: str, base_override: Optional[Dict[str, str]] = None):
    base = dict(base_override) if base_override is not None else dict(resolve_market(market))
    base_mint_value = base.get("base_mint") or DEFAULT_BASE_MINT
    base["base_mint"] = str(base_mint_value)
    if "custody" not in base and base.get("custody_base"):
        base["custody"] = base["custody_base"]
    quote_custody = base.get("custody_quote")
    if quote_custody and "collateralCustody" not in base:
        base["collateralCustody"] = quote_custody
    if quote_custody and "collateral_custody" not in base:
        base["collateral_custody"] = quote_custody
    quote_mint = base.get("quote_mint") or DEFAULT_QUOTE_MINT
    if quote_mint:
        quote_mint = str(quote_mint)
        base["quote_mint"] = quote_mint
    if quote_mint and "input_mint" not in base:
        base["input_mint"] = quote_mint
    if not base.get("oracle"):
        base["oracle"] = DEFAULT_ORACLE_PUBKEY
    return base, resolve_extra_account


def _pdas(
    owner: Pubkey,
    market: str,
    program_id: Pubkey,
    market_mint: Optional[str],
) -> Tuple[Pubkey, Pubkey, int]:
    from backend.perps.pdas import (
        derive_position_request_pda,
        position_pda,
        position_request_pda,
    )

    position = position_pda(owner, market, program_id, market_mint=market_mint)
    counter = int(time.time())
    try:
        request = position_request_pda(owner, market, program_id, market_mint=market_mint)
    except Exception:
        try:
            request = derive_position_request_pda(owner, market, program_id)  # type: ignore[arg-type]
        except TypeError:
            request = derive_position_request_pda(position, counter)
        except Exception:
            request = derive_position_request_pda(position, counter)
    return position, request, counter


# ---------- public API ----------
def _metas_index_before_programs(ix_idl: dict, mapping: dict) -> int:
    """
    Return the metas index where program accounts start (token_program or system program),
    counting only accounts that will actually be appended (i.e., present or required).
    We insert unknown non-IDL accounts right before this index so they sit in the
    'non-program' account range Anchor validates first.
    """

    accounts = ix_idl.get("accounts") or []
    metas_idx = -1
    for acc_def in accounts:
        nm = str(acc_def.get("name", ""))
        nm_lc = nm.lower()
        is_opt = bool(acc_def.get("isOptional"))
        present = nm in mapping

        if nm_lc in (
            "token_program",
            "tokenprogram",
            "system_program",
            "systemprogram",
            "associated_token_program",
            "associatedtokenprogram",
        ):
            return metas_idx + 1

        if present or not is_opt:
            metas_idx += 1

    return metas_idx + 1


def _metas_from(ix_idl: Dict[str, Any], mapping: Dict[str, Pubkey]) -> List[AccountMeta]:
    """
    Build metas strictly in IDL order, skipping only missing optionals.
    Also *force* the canonical Position PDA to avoid seed drift between helpers and program.
    """

    metas: List[AccountMeta] = []
    for acc_def in (ix_idl.get("accounts") or []):
        nm = str(acc_def["name"])
        is_signer = bool(acc_def.get("isSigner"))
        is_writable = bool(acc_def.get("isMut"))
        is_opt = bool(acc_def.get("isOptional"))

        if nm.lower() == "position":
            metas.append(AccountMeta(EXPECTED_POSITION_PDA, is_signer, is_writable))
            continue

        if nm not in mapping:
            if is_opt:
                continue
            raise KeyError(nm)

        metas.append(AccountMeta(mapping[nm], is_signer, is_writable))
    return metas


def build_metas_from_mapping(
    account_mapping: Dict[str, Pubkey],
    idl_ix: Dict[str, Any],
    existing_remaining: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[AccountMeta], List[Dict[str, Any]]]:
    required_metas = _metas_from(idl_ix, account_mapping)
    remaining = list(existing_remaining) if existing_remaining else []
    metas: List[AccountMeta] = list(required_metas)
    for rem in remaining:
        metas.append(
            AccountMeta(
                rem["pubkey"],
                bool(rem.get("is_signer", False)),
                bool(rem.get("is_writable", False)),
            )
        )
    return metas, remaining


def _dump_idl_and_metas(ix_idl: Dict[str, Any], metas: List[AccountMeta]) -> None:
    try:
        rows = []
        accs = ix_idl.get("accounts") or []
        for i, m in enumerate(metas):
            nm = accs[i]["name"] if i < len(accs) else "<extra>"
            rows.append(f"  [{i:02d}] {nm:24s} {str(m.pubkey)}")
        print("[perps] metas detail:\n" + "\n".join(rows))
    except Exception:
        pass


def _force_all_tokenkeg_to_atoken(metas: List[AccountMeta]) -> List[AccountMeta]:
    """Legacy shim: previously rewrote stray Tokenkeg accounts to AToken.

    Now acts as a no-op to avoid clobbering validated token program slots while
    keeping the call sites intact for logging parity with earlier builds.
    """

    return list(metas)


def _force_token_program_slot(ix_idl: Dict[str, Any],
                              mapping: Dict[str, Pubkey],
                              metas: List[AccountMeta]) -> List[AccountMeta]:
    """Legacy shim retained for compatibility; now returns metas unchanged."""

    return list(metas)


# --- DRY RUN HARNESS ---------------------------------------------------------


def _name_metas(ix_idl: Dict[str, Any], metas: List[AccountMeta]) -> List[Dict[str, Any]]:
    """Return [{idx, name, pubkey, is_signer, is_writable}] in IDL order (plus extras)."""
    out: List[Dict[str, Any]] = []
    accs = ix_idl.get("accounts") or []
    for i, m in enumerate(metas):
        name = accs[i]["name"] if i < len(accs) else "<extra>"
        out.append(
            {
                "idx": i,
                "name": name,
                "pubkey": str(m.pubkey),
                "is_signer": bool(m.is_signer),
                "is_writable": bool(m.is_writable),
            }
        )
    return out


def _parse_err_code_and_msg(logs: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """Best-effort scrape of Anchor error code + descriptive line from logs."""
    code = None
    msg = None
    for line in logs:
        if "Error Code:" in line:
            # Example: "Error Code: InvalidCollateralAccount. Error Number: 6006."
            #          "Error Message: Invalid collateral account."
            parts = line.split("Error Code:", 1)[-1].strip()
            code = parts.split(".")[0].strip()
        if "Error Message:" in line:
            msg = line.split("Error Message:", 1)[-1].strip()
    return code, msg


def _metas_and_raw_for_mapping(
    ix_idl: Dict[str, Any],
    mapping: Dict[str, Pubkey],
    wallet: Keypair,
    owner: Pubkey,
    program_id: Pubkey,
    data: bytes,
) -> Tuple[List[AccountMeta], List[Dict[str, Any]], str]:
    """Build metas + raw tx from a current mapping snapshot."""
    metas, remaining = build_metas_from_mapping(mapping, ix_idl, existing_remaining=None)
    # mirror your existing prints & guardrails to keep parity
    _print_idl_accounts_audit(ix_idl, mapping)
    _print_remaining_accounts(metas, ix_idl)
    _dump_idl_and_metas(ix_idl, metas)

    ixs: List[Instruction] = []
    ixs += compute_budget_ixs()
    ixs.append(Instruction(program_id, data, metas))

    bh = recent_blockhash()
    msg = MessageV0.try_compile(
        payer=owner,
        instructions=ixs,
        address_lookup_table_accounts=[],
        recent_blockhash=bh,
    )
    tx_local = VersionedTransaction(msg, [wallet])
    raw_tx = base64.b64encode(bytes(tx_local)).decode()
    return metas, remaining, raw_tx


def dry_run_open_position_request(
    wallet: Keypair,
    market: str,
    side: Literal["long", "short"],
    size_usd: float,
    collateral_usd: float,
    tp: Optional[float] = None,
    sl: Optional[float] = None,
    max_recover: int = 6,
    log_limit: int = 240,
    try_custody_swap_on_6006: bool = True,
) -> Dict[str, Any]:
    """
    Prepare & simulate the 'create increase position market request' flow but never send.
    Returns a structured report with mapping, metas, and step-by-step logs/diagnostics.
    """
    idl = load_idl()
    program_id = program_id_from_idl(idl)
    owner = wallet.pubkey()

    # Market registry + PDAs
    market_info = resolve_market(market)
    market_mint = str(market_info.get("base_mint") or DEFAULT_BASE_MINT)
    position, request, counter_seed = _pdas(owner, market, program_id, market_mint)
    base_accounts, resolve_extra = _market_info(market, market_info)

    # Instruction selection (same heuristic as live open) -------------
    ix_idl = _find_ix_any(
        idl,
        candidates=[
            "createincreasepositionmarketrequest",
            "increaseposition4",
            "instantincreaseposition",
            "create_increase_position_request",
            "increase_position_request",
            "create_open_position_request",
            "open_position_request",
            "create_position_request",
            "create_trade_request",
            "trade_request",
            "position_request",
        ],
        fallback_any=["request", "increase"],
    )

    types_idx = _types_index(idl)
    idl_args = ix_idl.get("args", []) or []
    args: Dict[str, Any] = {}

    # Build args exactly like live path --------------------------------
    referral_env = os.getenv("JUP_PERPS_REFERRAL", "").strip()
    referral_pk = referral_env if referral_env else str(owner)

    def _build_struct(def_name: str) -> Dict[str, Any]:
        type_def = types_idx.get(def_name) or {}
        fields: List[Dict[str, Any]] = (
            type_def.get("fields") or [] if type_def.get("kind") == "struct" else []
        )
        out: Dict[str, Any] = {}
        for field in fields:
            fname = field["name"]
            fkind = field["type"]
            fl = fname.lower()
            if fl in ("sizeusddelta", "sizeusd", "size", "amount", "makingamount"):
                out[fname] = int(size_usd * USD_SCALE)
            elif fl in ("collateraltokendelta", "collateralusd", "collateral", "margin"):
                out[fname] = int(collateral_usd * USD_SCALE)
            elif fl in ("side", "direction"):
                out[fname] = "Long" if side == "long" else "Short"
            elif fl in ("priceslippage", "slippage", "maxslippagebps"):
                out[fname] = 0
            elif fl in ("jupiterminimumout", "minimumout", "minout"):
                out[fname] = None
            elif fl in ("counter",):
                out[fname] = int(time.time())
            elif fl in ("tp", "tpprice", "takeprofitprice"):
                out[fname] = int((tp or 0) * USD_SCALE)
            elif fl in ("sl", "slprice", "stoplossprice"):
                out[fname] = int((sl or 0) * USD_SCALE)
            elif "referr" in fl and _is_pk_like(fkind):
                out[fname] = referral_pk
            elif "positionrequest" in fl and _is_pk_like(fkind):
                out[fname] = str(request)
            elif "position" in fl and _is_pk_like(fkind):
                out[fname] = str(position)
            elif _is_pk_like(fkind):
                out[fname] = str(owner)
            elif fkind == "bool":
                out[fname] = False
            elif isinstance(fkind, dict) and "option" in fkind:
                out[fname] = None
            else:
                out[fname] = 0
        return out

    if len(idl_args) == 1 and isinstance(idl_args[0].get("type"), dict) and "defined" in idl_args[0]["type"]:
        def_name = str(idl_args[0]["type"]["defined"])
        args[idl_args[0]["name"]] = _build_struct(def_name)
    else:
        for arg in idl_args:
            name = arg["name"]
            type_def = arg["type"]
            key = str(name).lower().replace("_", "")
            if key in ("referral", "referrer", "referralaccount", "referreraccount", "refaccount", "ref"):
                args[name] = referral_pk
            elif key in ("owner", "user", "trader", "authority"):
                args[name] = str(owner)
            elif key in ("side", "direction"):
                args[name] = 0 if side == "long" else 1
            elif key in ("sizeusd", "size", "amount", "makingamount"):
                args[name] = int(size_usd * USD_SCALE)
            elif key in ("collateralusd", "collateral", "margin"):
                args[name] = int(collateral_usd * USD_SCALE)
            elif key in ("tp", "tpprice", "takeprofitprice"):
                args[name] = int((tp or 0) * USD_SCALE)
            elif key in ("sl", "slprice", "stoplossprice"):
                args[name] = int((sl or 0) * USD_SCALE)
            elif "positionrequest" in key and _is_pk_like(type_def):
                args[name] = str(request)
            elif key.startswith("position") and _is_pk_like(type_def):
                args[name] = str(position)
            elif _is_pk_like(type_def):
                args[name] = str(owner)
            elif type_def == "bool":
                args[name] = False
            else:
                args[name] = 0

    # Input mint used to derive ATAs
    input_mint_value = base_accounts.get("input_mint")
    input_mint: Optional[Pubkey] = None
    if input_mint_value and "ReplaceWith" not in input_mint_value:
        input_mint = Pubkey.from_string(str(input_mint_value))

    # Map accounts (canonical programs in their proper slots)
    metas_ignore, base_mapping = map_accounts(
        ix_idl, owner, position, request, base_accounts, market, resolve_extra, program_id, input_mint
    )

    # Use the real PDAs discovered earlier
    mapping = dict(base_mapping)
    mapping["position"] = EXPECTED_POSITION_PDA
    print(f"[perps] FORCE position (dry-run) → {str(EXPECTED_POSITION_PDA)}")
    mapping["positionRequest"] = request
    mapping["position_request"] = request

    # Canonical programs (SPL Token in tokenProgram slot; ATA program in associatedTokenProgram)
    mapping["tokenProgram"] = SPL_TOKEN_PROGRAM
    mapping["token_program"] = SPL_TOKEN_PROGRAM
    mapping["associatedTokenProgram"] = ASSOCIATED_TOKEN_PROG
    mapping["associated_token_program"] = ASSOCIATED_TOKEN_PROG

    # Ensure the request's ATA owner is the *request PDA* (not wallet)
    if input_mint:
        try:
            mapping["positionRequestAta"] = _derive_ata(mapping["positionRequest"], input_mint)
            mapping["position_request_ata"] = mapping["positionRequestAta"]
        except Exception as _:
            pass

    # Serialize instruction data
    data = build_data(ix_idl, args, types_idx)

    # ---- simulate (multi-step) without send -----------------------------------
    report: Dict[str, Any] = {
        "programId": str(program_id),
        "instruction": ix_idl.get("name"),
        "market": market,
        "side": side,
        "args": args,
        "position": str(EXPECTED_POSITION_PDA),
        "positionRequest": str(mapping["positionRequest"]),
        "positionRequestAta": str(mapping.get("positionRequestAta", "")),
        "inputMint": str(input_mint) if input_mint else None,
        "baseAccounts": {k: str(v) for k, v in base_accounts.items()},
        "mapping": {k: str(v) for k, v in mapping.items()},
        "steps": [],
        "ok": False,
    }

    def _simulate_step(label: str, m: Dict[str, Pubkey]) -> Tuple[bool, List[str], List[AccountMeta], str]:
        metas, rem, raw = _metas_and_raw_for_mapping(ix_idl, m, wallet, owner, program_id, data)
        sim = rpc("simulateTransaction", [raw, {"encoding": "base64", "sigVerify": False, "replaceRecentBlockhash": True}])
        value = sim.get("value") or {}
        logs = (value.get("logs") or [])[:log_limit]
        ok = not bool(value.get("err"))
        # Capture per-step info
        report["steps"].append(
            {
                "label": label,
                "ok": ok,
                "unknownAccount": _parse_unknown_account(logs),
                "rightPdaHint": _parse_anchor_right_pda(logs),
                "errorCode": _parse_err_code_and_msg(logs)[0],
                "errorMessage": _parse_err_code_and_msg(logs)[1],
                "metas": _name_metas(ix_idl, metas),
                "logs": logs,
            }
        )
        return ok, logs, metas, raw

    ok, logs, metas, raw = _simulate_step("initial", mapping)
    if not ok:
        # 1) PDA adoption guided by which account triggered ConstraintSeeds
        seed_hint = _parse_anchor_constraint_seeds(logs)
        if seed_hint:
            acct_name, right_b58 = seed_hint
            acct_lc = acct_name.lower()
            if "position_request" in acct_lc and input_mint:
                _rebuild_after_request_adopt(mapping, right_b58, input_mint)
                ok, logs, metas, raw = _simulate_step("after PR adopt", mapping)
            elif acct_lc == "position":
                # Trust the program’s canonical position PDA for this run
                try:
                    mapping["position"] = Pubkey.from_string(right_b58)
                    ok, logs, metas, raw = _simulate_step("after position adopt", mapping)
                except Exception:
                    pass

    # 2) Collateral error targeted handling (6006) — adopt from logs, then (optionally) swap
    if not ok:
        code, _msg = _parse_err_code_and_msg(logs)
        if code and "InvalidCollateralAccount" in code:
            # Try to read the pair the program printed and set mapping explicitly
            lr = _parse_invalid_collateral(logs)
            if lr:
                left_b58, right_b58 = lr
                try:
                    mapping["custody"] = Pubkey.from_string(left_b58)
                    mapping["collateralCustody"] = Pubkey.from_string(right_b58)
                except Exception:
                    pass
                ok, logs, metas, raw = _simulate_step("after collateral adopt", mapping)

            # If still failing, try swapping custody<->collateralCustody (some IDLs invert names)
            if try_custody_swap_on_6006 and not ok and mapping.get("custody") and mapping.get("collateralCustody"):
                swap_mapping = dict(mapping)
                swap_mapping["custody"], swap_mapping["collateralCustody"] = mapping["collateralCustody"], mapping["custody"]
                ok, logs, metas, raw = _simulate_step("after custody↔collateral swap", swap_mapping)
                if ok:
                    mapping.update(swap_mapping)

    # 3) Unknown account recovery loop (append to remaining accounts)
    recover = 0
    last_unknown = None
    while not ok and recover < max_recover:
        unknown_b58 = _parse_unknown_account(logs)
        if not unknown_b58:
            # nothing left to infer
            break
        if last_unknown == unknown_b58:
            make_writable = _saw_writable_privilege_escalated(logs)
            make_signer = _saw_unauthorized_signer_or_writable(logs) and not make_writable
            _append_remaining_account([], unknown_b58, signer=make_signer, writable=make_writable)  # logged for parity
        else:
            _append_remaining_account([], unknown_b58, signer=False, writable=False)  # logged for parity
        # NOTE: We do not persist remaining accounts inside the mapping here; the function above is used only for logging parity.
        ok, logs, metas, raw = _simulate_step(f"after remaining-account append #{recover+1}", mapping)
        last_unknown = unknown_b58
        recover += 1

    report["ok"] = bool(ok)
    # Include final snapshot of mapping & metas we ended up with
    metas_final, _, _raw_final = _metas_and_raw_for_mapping(ix_idl, mapping, wallet, owner, program_id, data)
    report["finalMapping"] = {k: str(v) for k, v in mapping.items()}
    report["finalMetas"] = _name_metas(ix_idl, metas_final)
    return report


# --- END DRY RUN HARNESS -----------------------------------------------------


def open_position_request(
    wallet: Keypair,
    market: str,
    side: Literal["long", "short"],
    size_usd: float,
    collateral_usd: float,
    tp: Optional[float] = None,
    sl: Optional[float] = None,
) -> Dict[str, Any]:
    idl = load_idl()
    program_id = program_id_from_idl(idl)
    owner = wallet.pubkey()
    market_info = resolve_market(market)
    market_mint = str(market_info.get("base_mint") or DEFAULT_BASE_MINT)
    position, request, counter = _pdas(owner, market, program_id, market_mint)
    base_accounts, resolve_extra = _market_info(market, market_info)

    # 1) find the correct "open/increase" request instruction, tolerant to IDL naming
    #    🔴 includes your exact IDL name: createincreasepositionmarketrequest
    ix_idl = _find_ix_any(
        idl,
        candidates=[
            "createincreasepositionmarketrequest",  # ← your IDL
            "increaseposition4",  # sometimes an instant model exists
            "instantincreaseposition",
            "create_increase_position_request",
            "increase_position_request",
            "create_open_position_request",
            "open_position_request",
            "create_position_request",
            "create_trade_request",
            "trade_request",
            "position_request",
        ],
        fallback_any=["request", "increase"],
    )

    types_idx = _types_index(idl)
    idl_args = ix_idl.get("args", []) or []
    args: Dict[str, Any] = {}

    referral_env = os.getenv("JUP_PERPS_REFERRAL", "").strip()
    referral_pk = referral_env if referral_env else str(owner)

    def _build_struct(def_name: str) -> Dict[str, Any]:
        type_def = types_idx.get(def_name) or {}
        fields: List[Dict[str, Any]] = (
            type_def.get("fields") or [] if type_def.get("kind") == "struct" else []
        )
        out: Dict[str, Any] = {}
        for field in fields:
            fname = field["name"]
            fkind = field["type"]
            fl = fname.lower()
            if fl in ("sizeusddelta", "sizeusd", "size", "amount", "makingamount"):
                out[fname] = int(size_usd * USD_SCALE)
            elif fl in ("collateraltokendelta", "collateralusd", "collateral", "margin"):
                out[fname] = int(collateral_usd * USD_SCALE)
            elif fl in ("side", "direction"):
                out[fname] = "Long" if side == "long" else "Short"
            elif fl in ("priceslippage", "slippage", "maxslippagebps"):
                out[fname] = 0
            elif fl in ("jupiterminimumout", "minimumout", "minout"):
                out[fname] = None
            elif fl in ("counter",):
                out[fname] = counter
            elif fl in ("tp", "tpprice", "takeprofitprice"):
                out[fname] = int((tp or 0) * USD_SCALE)
            elif fl in ("sl", "slprice", "stoplossprice"):
                out[fname] = int((sl or 0) * USD_SCALE)
            elif "referr" in fl and _is_pk_like(fkind):
                out[fname] = referral_pk
            elif "positionrequest" in fl and _is_pk_like(fkind):
                out[fname] = str(request)
            elif "position" in fl and _is_pk_like(fkind):
                out[fname] = str(position)
            elif _is_pk_like(fkind):
                out[fname] = str(owner)
            elif fkind == "bool":
                out[fname] = False
            elif isinstance(fkind, dict) and "option" in fkind:
                out[fname] = None
            else:
                out[fname] = 0
        return out

    if (
        len(idl_args) == 1
        and isinstance(idl_args[0].get("type"), dict)
        and "defined" in idl_args[0]["type"]
    ):
        def_name = str(idl_args[0]["type"]["defined"])
        args[idl_args[0]["name"]] = _build_struct(def_name)
    else:
        for arg in idl_args:
            name = arg["name"]
            type_def = arg["type"]
            key = str(name).lower()
            normalized = key.replace("_", "")

            if normalized in (
                "referral",
                "referrer",
                "referralaccount",
                "referreraccount",
                "refaccount",
                "ref",
            ):
                args[name] = referral_pk
            elif normalized in ("owner", "user", "trader", "authority"):
                args[name] = str(owner)
            elif normalized in ("side", "direction"):
                args[name] = 0 if side == "long" else 1
            elif normalized in ("sizeusd", "size", "amount", "makingamount"):
                args[name] = int(size_usd * USD_SCALE)
            elif normalized in ("collateralusd", "collateral", "margin"):
                args[name] = int(collateral_usd * USD_SCALE)
            elif normalized in ("tp", "tpprice", "takeprofitprice"):
                args[name] = int((tp or 0) * USD_SCALE)
            elif normalized in ("sl", "slprice", "stoplossprice"):
                args[name] = int((sl or 0) * USD_SCALE)
            elif "positionrequest" in normalized and _is_pk_like(type_def):
                args[name] = str(request)
            elif normalized.startswith("position") and _is_pk_like(type_def):
                args[name] = str(position)
            elif _is_pk_like(type_def):
                args[name] = str(owner)
            elif type_def == "bool":
                args[name] = False
            else:
                args[name] = 0

    try:
        print("[perps] arg map:", json.dumps(args))
    except Exception:
        pass

    input_mint_value = base_accounts.get("input_mint")
    input_mint: Optional[Pubkey] = None
    if input_mint_value and "ReplaceWith" not in input_mint_value:
        input_mint = _pubkey_from_str(input_mint_value, market, "input_mint")

    metas, account_mapping = map_accounts(
        ix_idl,
        owner,
        position,
        request,
        base_accounts,
        market,
        resolve_extra,
        program_id,
        input_mint,
    )

    # Use exact PDAs resolved from registry/PDA helpers
    mapping = dict(account_mapping)
    request = mapping.get("positionRequest", request)

    try:
        pr_str = str(request)
        params = args.get("params")
        if isinstance(params, dict):
            for key in list(params.keys()):
                if isinstance(key, str) and "positionrequest" in key.lower():
                    params[key] = pr_str
        for key in list(args.keys()):
            if isinstance(key, str) and key != "params" and "positionrequest" in key.lower():
                args[key] = pr_str
    except Exception:
        pass

    print(
        f"[perps] DERIVED positionRequest from counter={counter} → {str(mapping['positionRequest'])}"
    )

    # --- normalize token program mapping for this instruction -------------------
    # Ensure canonical program mappings are set explicitly for downstream metas.
    mapping["tokenProgram"] = SPL_TOKEN_PROGRAM
    mapping["token_program"] = SPL_TOKEN_PROGRAM
    mapping["associatedTokenProgram"] = ASSOCIATED_TOKEN_PROG
    mapping["associated_token_program"] = ASSOCIATED_TOKEN_PROG
    # ---------------------------------------------------------------------------

    # Audit the declared accounts vs what we’re about to send
    _print_idl_accounts_audit(ix_idl, mapping)

    metas = _metas_from(ix_idl, mapping)
    _print_remaining_accounts(metas, ix_idl)
    metas = _force_token_program_slot(ix_idl, mapping, metas)
    metas = _force_all_tokenkeg_to_atoken(metas)
    _dump_idl_and_metas(ix_idl, metas)

    try:
        names = [a.get("name") for a in (ix_idl.get("accounts") or [])]
        print("[perps] metas normalized:", {n: str(mapping[n]) for n in names if n in mapping})
    except Exception:
        pass

    try:
        names = [a.get("name") for a in ix_idl.get("accounts", [])]
        sent = {n: str(mapping[n]) for n in names if n in mapping}
        print("[perps] accounts for open-request:", sent)
    except Exception:
        pass

    data = build_data(ix_idl, args, types_idx)

    def _send_with(
        _override: Dict[str, Pubkey] | None = None,
        _simulate: bool = False,
    ) -> str:
        # Effective mapping = normalized base + any one-off overrides
        effective = dict(mapping)
        if _override:
            effective.update(_override)

        # Use whatever PDAs are in the current mapping

        _metas = _metas_from(ix_idl, effective)
        _metas = _force_token_program_slot(ix_idl, effective, _metas)
        _metas = _force_all_tokenkeg_to_atoken(_metas)
        def _guardrails(curr_mapping: Dict[str, Pubkey], metas: List[AccountMeta]) -> None:
            required_names = [a.get("name") for a in ix_idl.get("accounts", [])]
            for idx, name in enumerate(required_names):
                if name is None or idx >= len(metas):
                    continue
                expected_pk: Optional[Pubkey]
                expected_pk = curr_mapping.get(name)
                if expected_pk is not None and metas[idx].pubkey != expected_pk:
                    raise AssertionError(f"Required account order mismatch at idx={idx} ({name})")

            token_prog_pk = curr_mapping.get("tokenProgram") or curr_mapping.get("token_program")
            assert token_prog_pk == SPL_TOKEN_PROGRAM, "tokenProgram must be SPL Token program id"

            request_pk = curr_mapping.get("positionRequest") or curr_mapping.get("position_request")
            request_ata = curr_mapping.get("positionRequestAta") or curr_mapping.get("position_request_ata")
            if request_pk and request_ata and input_mint:
                try:
                    expected_ata = _derive_ata(request_pk, input_mint)
                    if expected_ata != request_ata:
                        print(
                            f"[perps] WARN: positionRequestAta {str(request_ata)} != expected {str(expected_ata)}"
                        )
                except Exception as ata_err:
                    print(f"[perps] WARN: unable to verify positionRequestAta owner: {ata_err}")

        def _make_raw_tx(metas: List[AccountMeta]) -> str:
            ixs: List[Instruction] = []
            ixs += compute_budget_ixs()
            ixs.append(Instruction(program_id, data, metas))

            bh = recent_blockhash()
            msg = MessageV0.try_compile(
                payer=owner,
                instructions=ixs,
                address_lookup_table_accounts=[],
                recent_blockhash=bh,
            )
            tx_local = VersionedTransaction(msg, [wallet])
            return base64.b64encode(bytes(tx_local)).decode()

        def _prepare_tx(curr_mapping: Dict[str, Pubkey], curr_remaining: Optional[List[Dict[str, Any]]] = None):
            metas, rem = build_metas_from_mapping(curr_mapping, ix_idl, existing_remaining=curr_remaining)
            _print_idl_accounts_audit(ix_idl, curr_mapping)
            _print_remaining_accounts(metas, ix_idl)
            _dump_idl_and_metas(ix_idl, metas)
            _guardrails(curr_mapping, metas)
            raw_tx = _make_raw_tx(metas)
            return metas, rem, raw_tx

        def _simulate_with_label(raw_tx: str, label: str) -> Tuple[bool, List[str]]:
            print(f"[perps] === simulateTransaction ({label}) :: BEGIN ===")
            sim_resp = rpc(
                "simulateTransaction",
                [raw_tx, {"encoding": "base64", "sigVerify": False, "replaceRecentBlockhash": True}],
            )
            val_resp = sim_resp.get("value") or {}
            logs_resp = val_resp.get("logs") or []
            print("[perps] simulate logs:\n  " + "\n  ".join(logs_resp[:240]))
            print(f"[perps] === simulateTransaction ({label}) :: END ===")
            return (not bool(val_resp.get("err"))), logs_resp

        print("[perps] open::_send_with ACTIVE", __file__)  # prove live code path

        remaining_accounts: List[Dict[str, Any]] = []
        metas, remaining_accounts, raw = _prepare_tx(effective, remaining_accounts)
        ok, logs = _simulate_with_label(raw, "initial")

        if not ok:
            seed_hint = _parse_anchor_constraint_seeds(logs)
            if seed_hint:
                acct_name, right_b58 = seed_hint
                acct_lc = acct_name.lower()

                if "position_request" in acct_lc:
                    if input_mint:
                        print(f"[perps] ADOPT position_request PDA → {right_b58}")
                        _rebuild_after_request_adopt(effective, right_b58, input_mint)
                        metas, remaining_accounts, raw = _prepare_tx(effective, remaining_accounts)
                        ok, logs = _simulate_with_label(raw, "after PR adopt")
                        if _is_invalid_program_id_for_token_program(logs):
                            raise RuntimeError(
                                "InvalidProgramId for token_program — VERIFY we never insert unknown into the required accounts area."
                            )

                elif acct_lc == "position":
                    # Update the position PDA to what the program expects, re-derive request & its ATA
                    try:
                        pos_pk = Pubkey.from_string(right_b58)
                        effective["position"] = pos_pk

                        if input_mint:
                            try:
                                counter_override = int(args.get("params", {}).get("counter", counter))
                            except Exception:
                                counter_override = int(counter)
                            effective["positionRequest"] = Pubkey.find_program_address(
                                [b"position_request", bytes(pos_pk), counter_override.to_bytes(8, "little")],
                                program_id,
                            )[0]
                            effective["position_request"] = effective["positionRequest"]
                            _rebuild_after_request_adopt(effective, str(effective["positionRequest"]), input_mint)

                        metas, remaining_accounts, raw = _prepare_tx(effective, remaining_accounts)
                        ok, logs = _simulate_with_label(raw, "after position adopt")
                    except Exception:
                        pass

        # Targeted recovery for Jupiter Perps "InvalidCollateralAccount" (6006).
        if not ok:
            lr = _parse_invalid_collateral(logs)
            if lr:
                left_b58, right_b58 = lr
                try:
                    left_pk = Pubkey.from_string(left_b58)
                    right_pk = Pubkey.from_string(right_b58)
                    # Respect what the program printed: Left=custody, Right=collateralCustody
                    effective["custody"] = left_pk
                    effective["collateralCustody"] = right_pk
                    print(
                        f"[perps] adopting custody={left_b58} collateralCustody={right_b58} from program logs"
                    )
                    metas, remaining_accounts, raw = _prepare_tx(effective, remaining_accounts)
                    ok, logs = _simulate_with_label(raw, "after collateral adopt")
                except Exception as _:
                    pass

        MAX_RECOVER = 6
        recover_count = 0
        last_unknown: Optional[str] = None

        while not ok and recover_count < MAX_RECOVER:
            unknown_b58 = _parse_unknown_account(logs)
            if not unknown_b58:
                print("[perps] no 'unknown account' pubkey found; cannot recover further")
                break

            if last_unknown == unknown_b58:
                make_writable = _saw_writable_privilege_escalated(logs)
                make_signer = _saw_unauthorized_signer_or_writable(logs) and not make_writable
                _append_remaining_account(remaining_accounts, unknown_b58, signer=make_signer, writable=make_writable)
            else:
                _append_remaining_account(remaining_accounts, unknown_b58, signer=False, writable=False)

            metas, remaining_accounts, raw = _prepare_tx(effective, remaining_accounts)
            ok, logs = _simulate_with_label(raw, "after remaining-account append")

            last_unknown = unknown_b58
            recover_count += 1

        if not ok:
            raise RuntimeError(
                "position_request adopt failed: simulation failed after remaining-account append (map required accounts by name)"
            )

        if _simulate:
            return json.dumps(
                {
                    "ok": True,
                    "stage": "ready-to-send",
                    "mapping": {
                        k: str(v) for k, v in effective.items() if isinstance(v, Pubkey)
                    },
                    "remaining": [
                        {
                            "pubkey": str(r["pubkey"]),
                            "is_signer": bool(r.get("is_signer")),
                            "is_writable": bool(r.get("is_writable")),
                        }
                        for r in remaining_accounts
                    ],
                    "raw_tx_base64": raw,
                }
            )

        return rpc(
            "sendTransaction",
            [raw, {"encoding": "base64", "skipPreflight": False, "maxRetries": 3}],
        )

    # try once with current mapping
    sig = _send_with(None, _simulate=False)
    return {"signature": sig, "programId": str(program_id), "market": market}


def close_position_request(wallet: Keypair, market: str) -> Dict[str, Any]:
    idl = load_idl()
    program_id = program_id_from_idl(idl)
    owner = wallet.pubkey()
    market_info = resolve_market(market)
    market_mint = str(market_info.get("base_mint") or DEFAULT_BASE_MINT)
    position, request, counter = _pdas(owner, market, program_id, market_mint)
    base_accounts, resolve_extra = _market_info(market, market_info)

    ix_idl = _find_ix_any(
        idl,
        candidates=[
            "createdecreasepositionmarketrequest",  # ← your IDL
            "updatedecreasepositionrequest2",  # some IDLs update a pre-existing request
            "closepositionrequest",  # explicit close request
            "decreaseposition4",
            "instantdecreaseposition",
            "create_close_position_request",
            "close_position_request",
            "decrease_position_request",
            "reduce_position_request",
            "close_request",
        ],
        fallback_any=["request", "decrease"],
    )
    types_idx = _types_index(idl)

    args: Dict[str, Any] = {}
    for arg in ix_idl.get("args", []):
        name = arg["name"]
        type_def = arg["type"]
        if isinstance(type_def, dict) and type_def.get("defined") == "ClosePositionRequestParams":
            args[name] = {}
        elif _is_pk_like(type_def):
            args[name] = str(owner)
        elif type_def == "bool":
            args[name] = False
        else:
            args[name] = 0

    input_mint_value = base_accounts.get("input_mint")
    input_mint: Optional[Pubkey] = None
    if input_mint_value and "ReplaceWith" not in input_mint_value:
        input_mint = _pubkey_from_str(input_mint_value, market, "input_mint")

    metas, account_mapping = map_accounts(
        ix_idl,
        owner,
        position,
        request,
        base_accounts,
        market,
        resolve_extra,
        program_id,
        input_mint,
    )

    # normalized working copy
    mapping = dict(account_mapping)

    # --- normalize token program mapping for this instruction -------------------
    # Ensure canonical program mappings are set explicitly for downstream metas.
    mapping["tokenProgram"] = SPL_TOKEN_PROGRAM
    mapping["token_program"] = SPL_TOKEN_PROGRAM
    mapping["associatedTokenProgram"] = ASSOCIATED_TOKEN_PROG
    mapping["associated_token_program"] = ASSOCIATED_TOKEN_PROG
    # ---------------------------------------------------------------------------

    metas = _metas_from(ix_idl, mapping)
    metas = _force_token_program_slot(ix_idl, mapping, metas)
    metas = _force_all_tokenkeg_to_atoken(metas)
    _dump_idl_and_metas(ix_idl, metas)

    try:
        names = [a.get("name") for a in (ix_idl.get("accounts") or [])]
        print("[perps] metas normalized:", {n: str(mapping[n]) for n in names if n in mapping})
    except Exception:
        pass

    data = build_data(ix_idl, args, types_idx)
    instructions: List[Instruction] = []
    instructions += compute_budget_ixs()
    instructions.append(Instruction(program_id, data, metas))

    blockhash = recent_blockhash()
    message = MessageV0.try_compile(
        payer=owner,
        instructions=instructions,
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash,
    )
    transaction = VersionedTransaction(message, [wallet])
    raw_tx = base64.b64encode(bytes(transaction)).decode()

    signature = rpc(
        "sendTransaction",
        [raw_tx, {"encoding": "base64", "skipPreflight": False, "maxRetries": 3}],
    )
    return {"signature": signature, "programId": str(program_id), "market": market}


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Jupiter Perps position request tools (dry‑run)")
    sub = parser.add_subparsers(dest="cmd")
    dr = sub.add_parser("dry-open", help="Simulate CreateIncreasePositionMarketRequest (no send)")
    dr.add_argument("--market", required=True, help="e.g. SOL-PERP")
    dr.add_argument("--side", choices=["long", "short"], required=True)
    dr.add_argument(
        "--size",
        type=float,
        required=True,
        help="Notional in USD (e.g. 11 for $11,000,000 at USD_SCALE=1e6)",
    )
    dr.add_argument(
        "--collateral",
        type=float,
        required=True,
        help="Collateral in USD units (same scaling)",
    )
    dr.add_argument("--tp", type=float, default=0.0)
    dr.add_argument("--sl", type=float, default=0.0)
    dr.add_argument("--out", type=str, default="", help="Optional path to write JSON report")
    args = parser.parse_args()

    if args.cmd == "dry-open":
        wallet = load_signer()
        rep = dry_run_open_position_request(
            wallet=wallet,
            market=args.market,
            side=args.side,
            size_usd=args.size,
            collateral_usd=args.collateral,
            tp=args.tp,
            sl=args.sl,
        )
        if args.out:
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump(rep, fh, indent=2)
            print(f"[perps] dry-run report → {args.out}")
        print(json.dumps(rep, indent=2))
    else:
        parser.print_help(sys.stderr)
        sys.exit(2)
