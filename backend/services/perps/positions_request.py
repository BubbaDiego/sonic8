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


def _collect_types(idl: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {entry["name"]: entry["type"] for entry in idl.get("types", [])}


def _encode_type(type_def: Any, value: Any, types: Dict[str, Dict[str, Any]]) -> bytes:
    if isinstance(type_def, str):
        if type_def == "bool":
            return (1 if bool(value) else 0).to_bytes(1, "little")
        if type_def == "u8":
            return int(value).to_bytes(1, "little", signed=False)
        if type_def == "u16":
            return int(value).to_bytes(2, "little", signed=False)
        if type_def == "u32":
            return int(value).to_bytes(4, "little", signed=False)
        if type_def == "i32":
            return int(value).to_bytes(4, "little", signed=True)
        if type_def == "u64":
            return int(value).to_bytes(8, "little", signed=False)
        if type_def == "i64":
            return int(value).to_bytes(8, "little", signed=True)
        if type_def == "u128":
            return int(value).to_bytes(16, "little", signed=False)
        if type_def == "i128":
            return int(value).to_bytes(16, "little", signed=True)
        if type_def == "publicKey":
            return bytes(Pubkey.from_string(value))
        raise RuntimeError(f"Unmapped IDL arg type: {type_def}")

    if not isinstance(type_def, dict):
        raise RuntimeError(f"Unsupported IDL type definition: {type_def}")

    if "option" in type_def:
        inner = type_def["option"]
        if value in (None, False, "", 0):
            return b"\x00"
        return b"\x01" + _encode_type(inner, value, types)

    if "defined" in type_def:
        name = type_def["defined"]
        defined = types.get(name)
        if not defined:
            # Some IDLs wrap types as {"defined": "<TypeName>"} even when the
            # definition is not present. Treat common enums as a single byte,
            # but if the name suggests a Pubkey alias, encode as such.
            if "pubkey" in str(name).lower():
                return bytes(Pubkey.from_string(value))
            return int(value).to_bytes(1, "little", signed=False)
        kind = defined.get("kind")
        if kind == "struct":
            fields = defined.get("fields", [])
            if value is None:
                raise RuntimeError(f"Struct '{name}' requires value")
            encoded = bytearray()
            for field in fields:
                fname = field["name"]
                ftype = field["type"]
                if fname not in value:
                    raise RuntimeError(f"Missing field '{fname}' for struct '{name}'")
                encoded += _encode_type(ftype, value[fname], types)
            return bytes(encoded)
        if kind == "enum":
            variants = defined.get("variants", [])
            variant_name: Optional[str]
            variant_payload: Any = None
            if isinstance(value, dict):
                if len(value) != 1:
                    raise RuntimeError(f"Enum '{name}' value must contain single variant")
                variant_name, variant_payload = next(iter(value.items()))
            else:
                variant_name = str(value)
            index = None
            for idx, variant in enumerate(variants):
                if variant["name"].lower() == (variant_name or "").lower():
                    index = idx
                    target_variant = variant
                    break
            if index is None:
                raise RuntimeError(f"Enum '{name}' has no variant '{variant_name}'")
            data = bytearray()
            data += index.to_bytes(1, "little", signed=False)
            fields = target_variant.get("fields", [])
            if fields:
                if variant_payload is None:
                    raise RuntimeError(f"Enum '{name}' variant '{variant_name}' requires payload")
                if isinstance(fields, list) and all(isinstance(f, dict) for f in fields):
                    for field in fields:
                        fname = field["name"]
                        ftype = field["type"]
                        data += _encode_type(ftype, variant_payload[fname], types)
                else:
                    # tuple-style variants
                    if not isinstance(variant_payload, list):
                        raise RuntimeError(f"Enum '{name}' variant '{variant_name}' expects list payload")
                    for idx, field in enumerate(fields):
                        data += _encode_type(field, variant_payload[idx], types)
            return bytes(data)
        raise RuntimeError(f"Unsupported defined type '{name}' with kind '{kind}'")

    raise RuntimeError(f"Unsupported IDL type definition: {type_def}")


def build_data(ix_idl: Dict[str, Any], arg_values: Dict[str, Any], idl_types: Dict[str, Dict[str, Any]]) -> bytes:
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
        data += _encode_type(type_def, arg_values[name], idl_types)
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
    referral_value = base_accounts.get("referral")
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
        elif name in ("tokenProgram", "token_program"):
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
        elif name in ("eventAuthority", "event_authority"):
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
        elif name in ("referral",):
            if referral_value and "ReplaceWith" not in referral_value:
                mapping[name] = _pubkey_from_str(referral_value, market, "referral")
            elif not acc.get("isOptional"):
                value = resolve_extra(market, name)
                mapping[name] = _pubkey_from_str(value, market, name)
            else:
                # optional and not configured; skip meta entirely
                pass
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

    types_map = _collect_types(idl)

    params: Dict[str, Any] = {}
    params["sizeUsdDelta"] = int(size_usd * USD_SCALE)
    params["collateralTokenDelta"] = int(collateral_usd * USD_SCALE)
    params["side"] = "Long" if side == "long" else "Short"
    params["priceSlippage"] = 0
    params["jupiterMinimumOut"] = None
    params["counter"] = counter

    args: Dict[str, Any] = {}
    # pick referral: env > owner (safe default)
    referral_env = os.getenv("JUP_PERPS_REFERRAL", "").strip()
    referral_pk = referral_env if referral_env else str(owner)

    def _type_kind(ty: Any) -> str:
        if isinstance(ty, str):
            return ty
        if isinstance(ty, dict):
            if "option" in ty:
                opt = ty["option"]
                if isinstance(opt, str):
                    return opt
            if "vec" in ty:
                vec = ty["vec"]
                if isinstance(vec, str):
                    return vec
        return ""

    def _is_pk_like(ty: Any) -> bool:
        if ty == "publicKey":
            return True
        if isinstance(ty, dict):
            if "option" in ty:
                return _is_pk_like(ty["option"])
            if "defined" in ty:
                return "pubkey" in str(ty["defined"]).lower()
        return False

    idl_args = ix_idl.get("args", []) or []

    # First pass: set values by name so we never miss referral-like args.
    for arg in idl_args:
        name = arg["name"]
        type_def = arg["type"]
        kind = _type_kind(type_def)
        raw_key = str(name).lower()
        key = raw_key.replace("_", "")

        if isinstance(type_def, dict) and type_def.get("defined") == "CreateIncreasePositionMarketRequestParams":
            args[name] = params
        elif key in ("referral", "referrer", "referralaccount", "referreraccount", "refaccount", "ref"):
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
        elif kind == "bool":
            # bools default to False (encoded as 0)
            args[name] = False

    # Second pass: fill anything still missing by type.
    for arg in idl_args:
        name = arg["name"]
        if name in args:
            continue

        type_def = arg["type"]
        kind = _type_kind(type_def)

        if _is_pk_like(type_def):
            args[name] = str(owner)
        elif kind == "bool":
            args[name] = False
        elif kind in ("u8", "u16", "u32", "i32", "u64", "i64", "u128", "i128"):
            args[name] = 0
        else:
            # defined/option/etc → set to zero-ish (encoder will handle options)
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

    try:
        names = [a.get("name") for a in ix_idl.get("accounts", [])]
        sent = {n: str(account_mapping[n]) for n in names if n in account_mapping}
        print("[perps] accounts for open-request:", sent)
    except Exception:
        pass

    data = build_data(ix_idl, args, types_map)

    def _send_with(_override: Dict[str, Pubkey] | None = None) -> str:
        # rebuild metas if we override token_program for the retry
        _metas: List[AccountMeta] = []
        if _override:
            for acc in ix_idl.get("accounts", []):
                nm = acc["name"]
                _metas.append(
                    AccountMeta(
                        _override.get(nm, account_mapping[nm]),
                        bool(acc.get("isSigner")),
                        bool(acc.get("isMut")),
                    )
                )
        else:
            _metas = metas

        instructions: List[Instruction] = []
        instructions += compute_budget_ixs()
        instructions.append(Instruction(program_id, data, _metas))

        blockhash = recent_blockhash()
        message = MessageV0.try_compile(
            payer=owner,
            instructions=instructions,
            address_lookup_table_accounts=[],
            recent_blockhash=blockhash,
        )
        transaction = VersionedTransaction(message, [wallet])
        raw_tx = base64.b64encode(bytes(transaction)).decode()
        return rpc(
            "sendTransaction",
            [raw_tx, {"encoding": "base64", "skipPreflight": False, "maxRetries": 3}],
        )

    # try once with current mapping
    try:
        sig = _send_with(None)
        return {"signature": sig, "programId": str(program_id), "market": market}
    except Exception as e:
        s = str(e)
        # If Anchor complains about InvalidProgramId for token_program, flip once (SPL <-> AToken) and retry.
        if "InvalidProgramId" in s and "token_program" in s:
            cur = account_mapping.get("tokenProgram") or account_mapping.get("token_program")
            alt = ASSOCIATED_TOKEN_PROG if cur == SPL_TOKEN_PROGRAM else SPL_TOKEN_PROGRAM
            override = dict(account_mapping)
            if "tokenProgram" in override:
                override["tokenProgram"] = alt
            if "token_program" in override:
                override["token_program"] = alt
            print(f"[perps] retrying open-request with token_program={str(alt)}")
            sig = _send_with(override)
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
    types_map = _collect_types(idl)

    args: Dict[str, Any] = {}
    for arg in ix_idl.get("args", []):
        type_def = arg["type"]
        if isinstance(type_def, dict) and type_def.get("defined") == "ClosePositionRequestParams":
            args[arg["name"]] = {}
        else:
            args[arg["name"]] = 0

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

    data = build_data(ix_idl, args, types_map)
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
