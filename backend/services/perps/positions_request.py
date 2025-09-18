from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Literal, Optional, Tuple

import requests
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from backend.services.perps.markets import resolve_market, resolve_extra_account

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
RPC_URL = os.getenv("RPC_URL", f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}")
CU_LIMIT = int(os.getenv("PERPS_CU_LIMIT", 800_000))
CU_PRICE = int(os.getenv("PERPS_CU_PRICE", 100_000))  # micro-lamports per CU
USD_SCALE = int(os.getenv("PERPS_USD_SCALE", 1_000_000))

SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
SPL_TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROG = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")

IDL_PATH = os.path.join(os.path.dirname(__file__), "idl", "jupiter_perpetuals.json")

DEFAULT_BASE_MINT = "So11111111111111111111111111111111111111112"
DEFAULT_QUOTE_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
DEFAULT_ORACLE_PUBKEY = "11111111111111111111111111111111"


def rpc(method: str, params: Any) -> Any:
    response = requests.post(
        RPC_URL,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"RPC error in {method}: {payload['error']}")
    return payload["result"]


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
    Try a list of candidate substrings (in order). If none match, pick the first instruction
    whose name contains ALL tokens in `fallback_any`.
    """

    entries = list(_idl_ix_map(idl).items())

    # direct contains (substring) search in order
    for cand in candidates:
        c = cand.lower()
        for name, ix in entries:
            if c in name:
                return ix

    # fallback heuristic: all tokens must be present
    tokens = [t.lower() for t in fallback_any if t]
    if tokens:
        for name, ix in entries:
            if all(t in name for t in tokens):
                return ix

    # last resort: show what we have to help you pick
    have = sorted(name for name, _ in entries)
    raise RuntimeError(f"Instruction not found; tried {candidates} / {fallback_any}. IDL has: {have}")


def _extract_expected_position_from_logs(logs: list[str]) -> str | None:
    """
    If simulate produced a ConstraintSeeds error for `position`, return the
    base58 after 'Right:' (the PDA the program expects). Otherwise None.
    """
    if not logs:
        return None
    # primary: scan around the 'account: position' line
    for i, line in enumerate(logs):
        if "account: position" in line and ("ConstraintSeeds" in line or "seeds constraint" in line.lower()):
            for j in range(i, min(i + 6, len(logs))):
                m = re.search(r"Right:\s*([1-9A-HJ-NP-Za-km-z]{32,})", logs[j])
                if m:
                    return m.group(1)
    # fallback: any 'Right: <pk>' line
    for line in logs:
        m = re.search(r"Right:\s*([1-9A-HJ-NP-Za-km-z]{32,})", line)
        if m:
            return m.group(1)
    return None


def _disc_from_idl(ix_idl: Dict[str, Any]) -> bytes:
    """
    Prefer the discriminator bytes embedded in the IDL (newer Anchor), otherwise
    fall back to sha256('global:<name>')[:8]. IDL shapes seen:
      { "discriminant": { "bytes": [..8..] } }
      { "discriminant": { "value": [..8..] } }
      { "discriminator": [..8..] }  # very old
    """

    disc = ix_idl.get("discriminant") or ix_idl.get("discriminator")
    if isinstance(disc, dict):
        arr = disc.get("bytes") or disc.get("value")
        if isinstance(arr, list) and len(arr) == 8:
            try:
                return bytes(int(x) & 0xFF for x in arr)
            except Exception:
                pass
    if isinstance(disc, list) and len(disc) == 8:
        try:
            return bytes(int(x) & 0xFF for x in disc)
        except Exception:
            pass

    # Fallback – derive from name (Anchor uses Rust snake_case)
    name = str(ix_idl.get("name", "")).strip()

    def snake_guess(raw: str) -> str:
        # Try to rebuild common rust snake_case from flat/camel names seen in your IDL
        s = raw.lower()
        tokens = [
            "create",
            "instant",
            "update",
            "increase",
            "decrease",
            "open",
            "close",
            "position",
            "market",
            "request",
            "swap",
            "liquidity",
            "pool",
            "config",
            "fees",
            "test",
            "set",
        ]
        i = 0
        out: List[str] = []
        while i < len(s):
            matched = False
            for token in sorted(tokens, key=len, reverse=True):
                if s[i:].startswith(token):
                    out.append(token)
                    i += len(token)
                    matched = True
                    break
            if not matched:
                match = re.match(r"\d+", s[i:])
                if match:
                    out.append(match.group(0))
                    i += len(match.group(0))
                else:
                    out.append(s[i])
                    i += 1
        merged: List[str] = []
        for part in out:
            if len(part) == 1 and part.isalpha() and merged:
                merged[-1] = merged[-1] + part
            else:
                merged.append(part)
        return "_".join(filter(None, merged))

    guesses = [snake_guess(name)]
    guesses += [
        "create_increase_position_market_request",
        "increase_position4",
        "instant_increase_position",
        name,
    ]
    for guess in guesses:
        sighash = hashlib.sha256(f"global:{guess}".encode("utf-8")).digest()[:8]
        return sighash

    return hashlib.sha256(f"global:{name}".encode("utf-8")).digest()[:8]


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
            # This program expects the Associated Token Program in this slot.
            # (Sim logs showed Left: ATokenGPv… Right: Tokenkeg…)
            mapping[name] = ASSOCIATED_TOKEN_PROG
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
def _metas_from(ix_idl: Dict[str, Any], mapping: Dict[str, Pubkey]) -> List[AccountMeta]:
    """
    Build metas strictly in IDL-declared order.
    - If an account is optional and absent in `mapping`, we skip it.
    - If an account is required and absent, we raise with a clear message.
    """

    metas: List[AccountMeta] = []
    for acc_def in (ix_idl.get("accounts") or []):
        nm = acc_def["name"]
        is_signer = bool(acc_def.get("isSigner"))
        is_writable = bool(acc_def.get("isMut"))
        is_opt = bool(acc_def.get("isOptional"))
        if nm not in mapping:
            if is_opt:
                continue
            raise KeyError(nm)
        metas.append(AccountMeta(mapping[nm], is_signer, is_writable))
    return metas


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
    EXPECTED_POSITION_PDA = Pubkey.from_string("7fpqAhNYnRegBsWDfoSNSLD6aDMXLQHzuruABfpnxYVv")
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

    # Collapse to one alias so we edit the actual map used to build metas
    mapping = account_mapping if "account_mapping" in locals() else acct

    # Extract counter (u64) from the struct arg you already built
    counter_from_args: Optional[int] = None
    try:
        # struct arg shape: {"params": { ... "counter": <int> }}
        params = args.get("params", {})
        if isinstance(params, dict) and params.get("counter") is not None:
            counter_from_args = int(params.get("counter"))
    except Exception:
        counter_from_args = None
    if counter_from_args is None:
        try:
            top_level_counter = args.get("counter")
            if top_level_counter is not None:
                counter_from_args = int(top_level_counter)
        except Exception:
            counter_from_args = None
    if counter_from_args is not None:
        counter = counter_from_args

    # Derive position_request PDA: ["position_request", position, counter_u64_le]
    try:
        pos_pda = mapping["position"]  # must already be a Pubkey; you hard-set or derived it earlier
        if not isinstance(pos_pda, Pubkey):
            pos_pda = Pubkey.from_string(str(pos_pda))
        pr_pda = Pubkey.find_program_address(
            [b"position_request", bytes(pos_pda), counter.to_bytes(8, "little")],
            program_id,
        )[0]
        mapping["positionRequest"] = pr_pda
        mapping["position_request"] = pr_pda  # cover snake/camel
        try:
            pr_str = str(pr_pda)
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
        request = pr_pda
        print(f"[perps] DERIVED positionRequest from counter={counter} → {str(pr_pda)}")
    except Exception as e:
        print(f"[perps] positionRequest derivation failed: {e}")
        # leave whatever was there; simulate will show Right: ... if wrong

    # --- normalize token program mapping for this instruction -------------------
    # Ensure canonical program mappings are set explicitly for downstream metas.
    mapping["tokenProgram"] = SPL_TOKEN_PROGRAM
    mapping["token_program"] = SPL_TOKEN_PROGRAM
    mapping["associatedTokenProgram"] = ASSOCIATED_TOKEN_PROG
    mapping["associated_token_program"] = ASSOCIATED_TOKEN_PROG
    # ---------------------------------------------------------------------------

    # ── force position PDA right before metas (prevents any late overwrite) ──
    mapping["position"] = EXPECTED_POSITION_PDA
    print(f"[perps] FORCE position → {str(EXPECTED_POSITION_PDA)}")

    metas = _metas_from(ix_idl, mapping)
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

        # ── force position PDA here too ──
        effective["position"] = EXPECTED_POSITION_PDA
        print(f"[perps] FORCE(position in _send_with) → {str(EXPECTED_POSITION_PDA)}")

        _metas = _metas_from(ix_idl, effective)
        _metas = _force_token_program_slot(ix_idl, effective, _metas)
        _metas = _force_all_tokenkeg_to_atoken(_metas)
        _dump_idl_and_metas(ix_idl, _metas)

        ixs: List[Instruction] = []
        ixs += compute_budget_ixs()
        ixs.append(Instruction(program_id, data, _metas))

        bh = recent_blockhash()
        msg = MessageV0.try_compile(
            payer=owner,
            instructions=ixs,
            address_lookup_table_accounts=[],
            recent_blockhash=bh,
        )
        tx = VersionedTransaction(msg, [wallet])
        raw = base64.b64encode(bytes(tx)).decode()

        if _simulate or os.getenv("PERPS_SIMULATE", "").strip() == "1":
            sim = rpc(
                "simulateTransaction",
                [
                    raw,
                    {
                        "encoding": "base64",
                        "sigVerify": False,
                        "replaceRecentBlockhash": True,
                    },
                ],
            )
            val = sim.get("value") or {}
            logs = val.get("logs") or []
            print("[perps] simulate logs:\n  " + "\n  ".join(logs[:60]))
            if val.get("err"):
                # 🔧 If position PDA seeds mismatch, adopt the expected PDA and retry once
                expect_pos = _extract_expected_position_from_logs(logs)
                if expect_pos:
                    try:
                        print(f"[perps] adopting expected position PDA → {expect_pos}")
                        effective["position"] = Pubkey.from_string(expect_pos)
                        # rebuild metas with corrected mapping
                        _metas = _metas_from(ix_idl, effective)
                        _metas = _force_token_program_slot(ix_idl, effective, _metas)
                        # if you kept the brute fixer, leave it here; it won't touch corrected slots
                        _metas = (
                            _force_all_tokenkeg_to_atoken(_metas)
                            if "_force_all_tokenkeg_to_atoken" in globals()
                            else _metas
                        )
                        _dump_idl_and_metas(ix_idl, _metas)

                        msg2 = MessageV0.try_compile(
                            payer=owner,
                            instructions=[
                                *compute_budget_ixs(),
                                Instruction(program_id, data, _metas),
                            ],
                            address_lookup_table_accounts=[],
                            recent_blockhash=recent_blockhash(),
                        )
                        tx2 = VersionedTransaction(msg2, [wallet])
                        raw2 = base64.b64encode(bytes(tx2)).decode()

                        # simulate corrected tx for visibility
                        sim2 = rpc(
                            "simulateTransaction",
                            [
                                raw2,
                                {
                                    "encoding": "base64",
                                    "sigVerify": False,
                                    "replaceRecentBlockhash": True,
                                },
                            ],
                        )
                        val2 = sim2.get("value") or {}
                        logs2 = val2.get("logs") or []
                        print("[perps] simulate (after position fix):\n  " + "\n  ".join(logs2[:60]))
                        if val2.get("err"):
                            raise RuntimeError(
                                "simulation failed after position fix; see logs above"
                            )

                        # send corrected tx
                        return rpc(
                            "sendTransaction",
                            [
                                raw2,
                                {
                                    "encoding": "base64",
                                    "skipPreflight": False,
                                    "maxRetries": 3,
                                },
                            ],
                        )
                    except Exception as _e:
                        print(f"[perps] position PDA fix attempt failed: {_e}")
                # not a seeds error or cannot parse → bubble
                raise RuntimeError("simulation failed; see server logs for details")

        return rpc(
            "sendTransaction",
            [raw, {"encoding": "base64", "skipPreflight": False, "maxRetries": 3}],
        )

    # try once with current mapping
    try:
        sig = _send_with(None, _simulate=False)
        return {"signature": sig, "programId": str(program_id), "market": market}
    except Exception as e:
        s = str(e)
        # If Anchor complains about InvalidProgramId for token_program, flip once (SPL <-> AToken) and retry.
        if "InvalidProgramId" in s and "token_program" in s:
            cur = mapping.get("tokenProgram") or mapping.get("token_program")
            alt = ASSOCIATED_TOKEN_PROG if cur == SPL_TOKEN_PROGRAM else SPL_TOKEN_PROGRAM
            override = dict(mapping)
            if "tokenProgram" in override:
                override["tokenProgram"] = alt
            if "token_program" in override:
                override["token_program"] = alt
            print(f"[perps] retrying open-request with token_program={str(alt)}")
            sig = _send_with(override, _simulate=False)
            return {"signature": sig, "programId": str(program_id), "market": market}
        # bubble anything else
        raise


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

    mapping = account_mapping if "account_mapping" in locals() else acct

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
