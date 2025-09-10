#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
Open a Jupiter Perps LONG SOL position with USDC collateral (Market).

This file is self-contained and implements three invocation paths:
  1) AnchorPy binder (Program.rpc / Program.methods)
  2) RAW Anchor send (8-byte sighash + Borsh-encoded params + IDL-ordered accounts)
  3) A final PROBE that deterministically tests the two remaining unknowns that an IDL
     cannot encode (enum index for `side`, and which mint/owner pair is expected for
     positionRequestAta).

Key implementation details:
  • Signer from "C:\sonic5\signer.txt" (mnemonic OR secret_b64).
  • RPC rotation/backoff for public endpoints (handles 429/transport errors).
  • ComputeBudget is ALWAYS added (1,000,000 CU + tiny priority fee) for simulate/send.
  • FRESH blockhash before simulate and send.
  • PositionRequestAta is derived as ATA(owner = PositionRequest PDA, mint = inputMint).
    For this script, `inputMint` is USDC (EPjF...), which matches our accounts.
  • Dumps params & accounts before invocation. Prints raw simulate logs and RPC errors.

Dependency for RAW path:
  (.venv) pip install borsh-construct

Recommended: Use a private mainnet RPC in .env (free dev tier works):
  RPC_URL=https://mainnet.helius-rpc.com/?api-key=YOUR_KEY
  RPC_LIST=https://solana-mainnet.g.alchemy.com/v2/YOUR_KEY,https://api.mainnet-beta.solana.com
"""

import os
import json
import base64
import argparse
import asyncio
import time
import hmac
import hashlib
import unicodedata
import struct
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any, Mapping

from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction, AccountMeta
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed, Processed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solana.exceptions import SolanaRpcException
from anchorpy import Provider, Wallet, Program, Idl, Context

try:
    from borsh_construct import U8, U64
except Exception:
    U8 = U64 = None  # surfaced later if RAW path is needed

# =========================
# Project constants
# =========================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SIGNER_FILE = PROJECT_ROOT / "signer.txt"

PERPS_PROGRAM_ID = Pubkey.from_string("PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu")
POOL             = Pubkey.from_string("5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq")
CUSTODY_SOL      = Pubkey.from_string("7xS2gz2bTp3fwCC7knJvUWTEU9Tycczu6VhJYKgi1wdz")
CUSTODY_USDC     = Pubkey.from_string("G18jKKXQwBbrHeiK3C9MRXhkHsLHf7XgCSisykV46EZa")

USDC_MINT = Pubkey.from_string(os.getenv("MINT_USDC", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"))

TOKEN_PROGRAM            = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
SYSTEM_PROGRAM           = Pubkey.from_string("11111111111111111111111111111111")
ASSOCIATED_TOKEN_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
RENT_SYSVAR_DEPRECATED   = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

IDL_PATH = Path(r"C:\sonic5\idl\jupiter_perps.json")

LAMPORTS_PER_SOL = 1_000_000_000
USDC_DECIMALS    = 6
MIN_SOL_LAMPORTS = int(os.getenv("MIN_SOL_LAMPORTS", "10000000"))  # 0.01 SOL

DEFAULT_RPC_FALLBACKS = [
    "https://api.mainnet-beta.solana.com",
    "https://rpc.ankr.com/solana",
]

DEBUG = True

# =========================
# Logging helpers
# =========================
def say(step: str): print(f"\n🟠 {step} …", flush=True)
def done(msg: str = "done"): print(f"   ✅ {msg}", flush=True)
def info(msg: str): print(f"   ℹ️  {msg}", flush=True)
def warn(msg: str): print(f"   ⚠️  {msg}", flush=True)
def err(msg: str): print(f"   ❌ {msg}", flush=True)
def d(msg: str):
    if DEBUG: print(f"   🐛 {msg}", flush=True)
def log(msg: str): print(msg, flush=True)

# =========================
# Signer file (mnemonic or secret_b64)
# =========================
def _parse_signer_file(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"): continue
        if "=" in line:
            k, v = line.split("=", 1)
            data[k.strip().lower()] = v.strip()
        else:
            if " " in line and len(line.split()) >= 12:
                data.setdefault("mnemonic", line)
    return data

def _mnemonic_to_seed(mnemonic: str, passphrase: str = "") -> bytes:
    m = unicodedata.normalize("NFKD", mnemonic.strip())
    s = "mnemonic" + unicodedata.normalize("NFKD", passphrase or "")
    return hashlib.pbkdf2_hmac("sha512", m.encode("utf-8"), s.encode("utf-8"), 2048, dklen=64)

def _hmac_sha512(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha512).digest()

def _slip10_ed25519_master(seed: bytes) -> Tuple[bytes, bytes]:
    I = _hmac_sha512(b"ed25519 seed", seed); return I[:32], I[32:]

def _slip10_ed25519_ckd_priv(k_par: bytes, c_par: bytes, i: int) -> Tuple[bytes, bytes]:
    if i < 0x80000000: raise ValueError("ed25519 CKD requires hardened indices")
    data = b"\x00" + k_par + struct.pack(">L", i)
    I = _hmac_sha512(c_par, data); return I[:32], I[32:]

def _parse_path(path: str) -> List[int]:
    path = path.strip()
    if path in ("m", "m/"): return []
    if not path.startswith("m/"): raise ValueError(f"Invalid path: {path}")
    out: List[int] = []
    for p in path[2:].split("/"):
        if not p: continue
        idx = int(p[:-1] if p.endswith("'") else p, 10)
        out.append(idx | 0x80000000)
    return out

def keypair_from_mnemonic(mnemonic: str, passphrase: str = "", path: str = "m/44'/501'/0'/0'") -> Keypair:
    seed = _mnemonic_to_seed(mnemonic, passphrase)
    k, c = _slip10_ed25519_master(seed)
    for i in _parse_path(path): k, c = _slip10_ed25519_ckd_priv(k, c, i)
    return Keypair.from_seed(k)

def keypair_from_b64(secret_b64: str) -> Keypair:
    try:
        raw = base64.b64decode(secret_b64)
    except Exception as e:
        raise SystemExit(f"❌ Secret is not valid base64: {e}")
    try:
        if raw and raw[:1] == b"[" and raw[-1:] == b"]":
            arr = json.loads(raw.decode("utf-8"))
            b   = bytes(arr)
            if len(b) == 64: return Keypair.from_bytes(b)
            raise SystemExit(f"❌ Decoded JSON keypair bytes={len(b)}; expected 64.")
    except Exception:
        pass
    n = len(raw)
    if n == 64: return Keypair.from_bytes(raw)
    if n == 32: return Keypair.from_seed(raw)
    raise SystemExit(f"❌ Unsupported secret length: {n}. Expected 32 or 64.")

def resolve_signer(args) -> Tuple[Keypair, str]:
    say("Resolving signer")
    signer_file = Path(args.signer_file).resolve() if args.signer_file else DEFAULT_SIGNER_FILE
    if not signer_file.exists(): raise SystemExit("❌ signer.txt not found (set --signer-file or create it).")
    info(f"Using SIGNER FILE: {signer_file}")
    kv = _parse_signer_file(signer_file)
    if "secret_b64" in kv:
        kp = keypair_from_b64(kv["secret_b64"])
    elif "mnemonic" in kv:
        kp = keypair_from_mnemonic(
            kv["mnemonic"],
            kv.get("mnemonic_passphrase", ""),
            kv.get("derivation_path", "m/44'/501'/0'/0'")
        )
    else:
        raise SystemExit("❌ signer.txt must contain secret_b64=... OR mnemonic=...")
    pub = str(kp.pubkey())
    done(f"pubkey {pub} (file)")
    return kp, pub

# =========================
# Env / RPC rotation with backoff
# =========================
from dotenv import load_dotenv

def load_endpoints() -> List[str]:
    # Always load the .env in the project root (C:\sonic5\.env)
    env_path = (Path(__file__).resolve().parents[2] / ".env")
    load_dotenv(dotenv_path=env_path, override=True)

    primary = os.getenv("RPC_URL", "").strip()
    extras  = [x.strip() for x in os.getenv("RPC_LIST", "").split(",") if x.strip()]

    endpoints: List[str] = []
    seen = set()

    def add(u: str):
        if u and u not in seen:
            seen.add(u); endpoints.append(u)

    # Prefer your private endpoint first
    add(primary)

    # Optional fallbacks (keep only Solana public; drop ankr to avoid 403)
    for e in extras:
        add(e)
    add("https://api.mainnet-beta.solana.com")

    # Debug: print the endpoints we’ll actually use
    info(f"RPC endpoints in order: {endpoints}")

    if not endpoints:
        raise SystemExit("❌ No RPC endpoints configured (set RPC_URL).")
    return endpoints


async def new_client(url: str) -> AsyncClient:
    return AsyncClient(url, commitment=Confirmed)

def is_rate_limit(exc: Exception) -> bool:
    s = repr(exc)
    return ("429" in s) or ("Too Many Requests" in s) or ("rate" in s.lower())

async def rpc_call_with_rotation(op_coro_factory, endpoints: List[str], start_idx: int = 0, attempts_per_endpoint: int = 2, sleep_base: float = 0.35):
    """
    op_coro_factory(endpoint_url) -> coroutine to await
    Rotates endpoints on HTTP 429 or SolanaRpcException; retries with small backoff.
    Returns (index, result_from_factory) on success.
    """
    if not endpoints: raise SystemExit("❌ No RPC endpoints configured (set RPC_URL).")
    n = len(endpoints)
    idx = start_idx % n
    last_exc = None
    for r in range(n):
        url = endpoints[idx]
        for att in range(attempts_per_endpoint):
            try:
                return idx, await op_coro_factory(url)
            except Exception as e:
                last_exc = e
                if is_rate_limit(e) or isinstance(e, SolanaRpcException):
                    warn(f"RPC @ {url} error: {e!r} (attempt {att+1}/{attempts_per_endpoint})")
                    await asyncio.sleep(sleep_base * (2 ** att))
                    continue
                warn(f"RPC @ {url} non-429 error: {e!r} — rotating …")
                break
        idx = (idx + 1) % n
    raise last_exc if last_exc else RuntimeError("RPC rotation exhausted without exception context")

# =========================
# IDL + PDAs
# =========================
async def ensure_idl() -> Idl:
    say("Ensuring IDL")
    if not IDL_PATH.exists(): raise SystemExit(f"❌ IDL JSON not found at {IDL_PATH}")
    text = IDL_PATH.read_text(encoding="utf-8")
    try: idl = Idl.from_json(text)
    except TypeError: idl = Idl.from_json(json.loads(text))
    done("IDL loaded from disk")
    return idl

def find_program_address(seeds: List[bytes], program_id: Pubkey) -> Pubkey:
    pda, _ = Pubkey.find_program_address(seeds, program_id); return pda
def derive_position_pda(owner: Pubkey, pool: Pubkey, custody: Pubkey, collateral_custody: Pubkey) -> Pubkey:
    return find_program_address([b"position", bytes(owner), bytes(pool), bytes(custody), bytes(collateral_custody)], PERPS_PROGRAM_ID)
def derive_position_request_pda(position: Pubkey, counter_u64: int) -> Pubkey:
    return find_program_address([b"position_request", bytes(position), counter_u64.to_bytes(8, "little")], PERPS_PROGRAM_ID)
def derive_event_authority() -> Pubkey:
    return find_program_address([b"__event_authority"], PERPS_PROGRAM_ID)
def derive_perpetuals_pda() -> Pubkey:
    return find_program_address([b"perpetuals"], PERPS_PROGRAM_ID)
def derive_ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    return find_program_address([bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)], ASSOCIATED_TOKEN_PROGRAM)

# =========================
# Balances
# =========================
async def fetch_spl_ui_balance(client: AsyncClient, owner: Pubkey, mint: Pubkey) -> Tuple[float, Pubkey, bool]:
    ata = derive_ata(owner, mint)
    acc_info = await client.get_account_info(ata)
    if acc_info.value is None: return 0.0, ata, False
    bal = await client.get_token_account_balance(ata)
    try: ui = float(bal.value.ui_amount_string or "0")
    except Exception: ui = 0.0
    return ui, ata, True

async def print_wallet_balances(client: AsyncClient, owner: Pubkey) -> Tuple[float, float, float, float]:
    say("Fetching wallet balances")
    lamports = (await client.get_balance(owner)).value
    sol = lamports / LAMPORTS_PER_SOL
    usdc, usdc_ata, usdc_exists = await fetch_spl_ui_balance(client, owner, USDC_MINT)
    WETH_MINT_LOCAL = Pubkey.from_string("7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs")
    WBTC_MINT_LOCAL = Pubkey.from_string("9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E")
    eth,  eth_ata,  eth_exists  = await fetch_spl_ui_balance(client, owner, WETH_MINT_LOCAL)
    btc,  btc_ata,  btc_exists  = await fetch_spl_ui_balance(client, owner, WBTC_MINT_LOCAL)
    log("— Wallet Balances —")
    log(f"SOL : {sol:.9f} ({lamports} lamports)")
    log(f"USDC: {usdc:.6f} (ATA: {str(usdc_ata)}{' ✅' if usdc_exists else ' ❌ not found'})")
    log(f"ETH : {eth:.6f} (wETH ATA: {str(eth_ata)}{' ✅' if eth_exists else ' ❌ not found'})")
    log(f"BTC : {btc:.6f} (wBTC ATA: {str(btc_ata)}{' ✅' if btc_exists else ' ❌ not found'})")
    log("--------------------")
    done("balances OK")
    return sol, usdc, eth, btc

# =========================
# Name helpers
# =========================
def _camel_to_snake(name: str) -> str:
    out = []
    for ch in name: out.append("_" + ch.lower() if ch.isupper() else ch)
    s = "".join(out); return s[1:] if s.startswith("_") else s

def _best_key(keys: List[str], target: str) -> Optional[str]:
    if target in keys: return target
    snake = _camel_to_snake(target)
    if snake in keys: return snake
    want = ["increase","position","request","market"]
    ranked = []
    for k in keys:
        l = k.lower()
        if "position" in l and "request" in l:
            ranked.append((sum(w in l for w in want), k))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked else None

def to_snake_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in (d or {}).items():
        s = []
        for ch in str(k): s.append("_" + ch.lower() if ch.isupper() else ch)
        key = "".join(s); key = key[1:] if key.startswith("_") else key
        out[key] = v
    return out

def deep_snake(x: Any) -> Any:
    if isinstance(x, dict):
        y: Dict[str, Any] = {}
        for k, v in x.items():
            s = []
            for ch in str(k): s.append("_" + ch.lower() if ch.isupper() else ch)
            key = "".join(s); key = key[1:] if key.startswith("_") else key
            y[key] = deep_snake(v)
        return y
    if isinstance(x, list):
        return [deep_snake(v) for v in x]
    return x

# =========================
# RAW IDL JSON helpers
# =========================
def _load_idl_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"❌ Failed to read IDL JSON at {path}: {e}")

def _find_ix_json(idl_json: dict, ix_name: str) -> Optional[dict]:
    for ix in idl_json.get("instructions", []):
        if ix.get("name") == ix_name: return ix
    snake = _camel_to_snake(ix_name)
    for ix in idl_json.get("instructions", []):
        if ix.get("name") == snake: return ix
    return None

def _find_type_json(idl_json: dict, name: str) -> Optional[dict]:
    for t in idl_json.get("types", []) or []:
        if t.get("name") == name: return t
    return None

def _enum_json_variant_index(idl_json: dict, enum_name: str, want: str) -> int:
    t = _find_type_json(idl_json, enum_name)
    want_low = (want or "").lower()
    if t and t.get("type", {}).get("kind") == "enum":
        for i, v in enumerate(t["type"].get("variants", [])):
            nm = v.get("name","")
            if nm.lower() == want_low: return i
        return 0
    return 0

def build_params_from_idl_json(idl_path: Path,
                               ix_name: str,
                               size_usd_6dp: int,
                               collateral_atoms: int,
                               max_price_usd_6dp: int,
                               counter_value: Optional[int] = None) -> Dict[str, Tuple[str, Any]]:
    j = _load_idl_json(idl_path)
    ix = _find_ix_json(j, ix_name)
    if not ix: raise SystemExit(f"❌ IDL JSON has no instruction named {ix_name}")
    args = ix.get("args", [])
    if not args:
        info("IDL JSON shows no args for this instruction."); return {}
    arg0 = args[0]
    t = arg0.get("type", {})
    defined = t.get("defined")
    fields = None
    if defined:
        type_def = _find_type_json(j, defined)
        if not type_def: raise SystemExit(f"❌ IDL JSON missing type definition {defined}")
        ty = type_def.get("type", {})
        if ty.get("kind") != "struct": raise SystemExit(f"❌ IDL JSON type {defined} is not a struct")
        fields = ty.get("fields", [])
        info(f"IDL JSON params '{arg0.get('name')}' → type '{defined}' fields: {[f['name'] for f in fields]}")
    else:
        ty = t
        fields = ty.get("fields", [])
        if ty.get("kind") != "struct": info("IDL JSON arg0 not a defined struct; using robust defaults.")

    params: Dict[str, Tuple[str, Any]] = {}
    if fields:
        for f in fields:
            nm = f.get("name"); nm_low = nm.lower()
            fty = f.get("type", {})
            if isinstance(fty, dict) and "defined" in fty:
                ename = fty["defined"]
                if nm_low == "side":
                    idx = _enum_json_variant_index(j, ename, "long")
                    params[nm] = ("enum_index", idx)
                else:
                    params[nm] = ("enum_index", 0)
            else:
                if "size" in nm_low and "usd" in nm_low: params[nm] = ("u64", size_usd_6dp)
                elif "collateral" in nm_low and "delta" in nm_low: params[nm] = ("u64", collateral_atoms)
                elif nm_low == "collateral_token_delta": params[nm] = ("u64", collateral_atoms)
                elif "slippage" in nm_low: params[nm] = ("u64", max_price_usd_6dp)
                elif "jupiter" in nm_low and "minimum" in nm_low: params[nm] = ("u64", 0)
                elif "trigger" in nm_low and "price" in nm_low: params[nm] = ("u64", 0)
                elif "trigger" in nm_low and ("above" in nm_low or "threshold" in nm_low): params[nm] = ("u8", 0)
                elif nm_low == "counter" and counter_value is not None: params[nm] = ("u64", counter_value)
                elif "entireposition" in nm_low or "entire_position" in nm_low: params[nm] = ("u8", 0)
                else: params[nm] = ("u64", 0)
    else:
        params = {
            "sizeUsdDelta": ("u64", size_usd_6dp),
            "collateralTokenDelta": ("u64", collateral_atoms),
            "side": ("enum_index", _enum_json_variant_index(j, "Side", "long")),
            "priceSlippage": ("u64", max_price_usd_6dp),
            "jupiterMinimumOut": ("u64", 0),
            "counter": ("u64", counter_value or 0),
        }

    info(f"Rendered params keys: {list(params.keys())}")
    return params

# =========================
# Binder resolution helpers
# =========================
def resolve_rpc_call(program: Program, ix_name: str) -> Tuple[Optional[Any], str, List[str]]:
    rpc_obj = program.rpc; rpc_names: List[str] = []; fn = None; chosen = ix_name
    if isinstance(rpc_obj, Mapping) or isinstance(rpc_obj, dict):
        rpc_names = list(rpc_obj.keys()); info(f"Program.rpc mapping keys: {', '.join(rpc_names)}")
        key = _best_key(rpc_names, ix_name);
        if key: chosen = key; fn = rpc_obj[key]
    else:
        rpc_names = [n for n in dir(rpc_obj) if not n.startswith("_")]; info(f"Program.rpc attributes: {', '.join(rpc_names)}")
        key = _best_key(rpc_names, ix_name);
        if key: chosen = key; fn = getattr(rpc_obj, key, None)
    return fn, chosen, rpc_names

def resolve_methods_builder(program: Program, ix_name: str) -> Tuple[Optional[Any], str, List[str]]:
    methods_obj = getattr(program, "methods", None)
    if methods_obj is None: return None, ix_name, []
    method_names: List[str] = []; builder = None; chosen = ix_name
    if isinstance(methods_obj, Mapping) or isinstance(methods_obj, dict):
        method_names = list(methods_obj.keys()); info(f"Program.methods mapping keys: {', '.join(method_names)}")
        key = _best_key(method_names, ix_name);
        if key: chosen = key; builder = methods_obj[key]
    else:
        method_names = [n for n in dir(methods_obj) if not n.startswith("_")]; info(f"Program.methods attributes: {', '.join(method_names)}")
        key = _best_key(method_names, ix_name);
        if key and hasattr(methods_obj, key): chosen = key; builder = getattr(methods_obj, key)
    return builder, chosen, method_names

# =========================
# RAW encoding (sighash + Borsh) and builder
# =========================
def _anchor_sighash(ix_name_snake: str) -> bytes:
    seed = f"global:{ix_name_snake}".encode("utf-8")
    return hashlib.sha256(seed).digest()[:8]

def _ix_name_for_hash(idl_json: dict, ix_name: str) -> str:
    """
    Return the exact Rust instruction name to use for Anchor's 8-byte discriminant.
    Anchor expects snake_case function names (not the camelCase names often found in IDL JSON).
    """
    ix = _find_ix_json(idl_json, ix_name)
    name = ix["name"] if ix and "name" in ix else ix_name
    # Anchor discriminant derives from the Rust fn name in snake_case:
    snake = _camel_to_snake(name)
    # Optional: debug print to be 100% sure what we're hashing
    d(f"sighash seed = 'global:{snake}'")
    return snake


def encode_params_borsh_from_typed(idl_json: dict, defined_name: str, typed_params: Dict[str, Tuple[str, Any]]) -> bytes:
    if U8 is None or U64 is None:
        raise SystemExit("❌ Missing dependency 'borsh-construct'. Run: pip install borsh-construct")
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

def compute_budget_ixs() -> list[Instruction]:
    """
    Always return two compute budget instructions:
      - setComputeUnitLimit(1_000_000)
      - setComputeUnitPrice(1000 micro-lamports)
    Built with keyword args + list[] so solders bindings are happy.
    """
    cb = Pubkey.from_string("ComputeBudget111111111111111111111111111111")
    # setComputeUnitLimit (discriminator 0x02) + u32 limit
    limit_bytes = bytes([2]) + int(1_000_000).to_bytes(4, "little")
    ix1 = Instruction(
        program_id=cb,
        accounts=[],                 # must be a list, not a tuple
        data=limit_bytes
    )
    # setComputeUnitPrice (discriminator 0x03) + u64 microLamports
    price_bytes = bytes([3]) + int(1_000).to_bytes(8, "little")
    ix2 = Instruction(
        program_id=cb,
        accounts=[],                 # must be a list, not a tuple
        data=price_bytes
    )
    return [ix1, ix2]


def build_raw_instruction(idl_path: Path,
                          ix_name: str,
                          params_typed: Dict[str, Tuple[str, Any]],
                          accounts_camel: Dict[str, Pubkey]) -> Instruction:
    j = _load_idl_json(idl_path)
    ix_json = _find_ix_json(j, ix_name)
    if not ix_json: raise SystemExit(f"❌ IDL JSON has no instruction named {ix_name}")

    req = [(a["name"], bool(a.get("isMut")), bool(a.get("isSigner"))) for a in ix_json.get("accounts", [])]
    info("IDL accounts (order, mut, signer): " + ", ".join([f"{n}(mut={m},signer={s})" for n,m,s in req]))

    name_for_hash = _ix_name_for_hash(j, ix_name)
    sighash = _anchor_sighash(name_for_hash)

    arg0 = (ix_json.get("args") or [])[0]
    defined = (arg0.get("type") or {}).get("defined")
    if not defined: raise SystemExit("❌ IDL arg type is not 'defined' struct; raw encoder needs a named struct.")
    params_bytes = encode_params_borsh_from_typed(j, defined, params_typed)
    data = sighash + params_bytes

    metas: List[AccountMeta] = []
    for acc in ix_json.get("accounts", []):
        nm = acc["name"]
        cand = accounts_camel.get(nm) or accounts_camel.get(nm[0].upper()+nm[1:])
        if cand is None:
            for k, v in accounts_camel.items():
                if _camel_to_snake(k) == nm:
                    cand = v; break
        if cand is None:
            raise SystemExit(f"❌ Missing account '{nm}' required by IDL")
        metas.append(AccountMeta(pubkey=cand,
                                 is_signer=bool(acc.get("isSigner")),
                                 is_writable=bool(acc.get("isMut"))))
    return Instruction(program_id=PERPS_PROGRAM_ID, accounts=metas, data=data)

# =========================
# Binder attempts (best-effort; safe to skip if you want)
# =========================
async def call_with_param_styles(program: Program, ix_name: str, accounts: dict, params_exact_obj: dict):
    accounts_snake = to_snake_keys(accounts)
    ctx = Context(accounts=accounts_snake, signers=[])
    snake = deep_snake(params_exact_obj)
    camel = params_exact_obj
    attempts = [
        ("wrapped/snake", {"params": snake}),
        ("naked/snake",   snake),
        ("wrapped/camel", {"params": camel}),
        ("naked/camel",   camel),
    ]
    try:
        say("Simulating (first binder variant)")
        sim = await program.simulate(ix_name, attempts[0][1] if isinstance(attempts[0][1], dict) else {"params": attempts[0][1]}, ctx=ctx)
        val = getattr(sim, "value", None)
        if val and getattr(val, "logs", None):
            info("simulation logs:"); [print(x) for x in val.logs]
    except Exception as e:
        warn(f"binder simulate raised: {e}")
    rpc_fn, chosen_rpc, _ = resolve_rpc_call(program, ix_name)
    if not rpc_fn:
        warn("No Program.rpc callable resolved"); return None
    for label, payload in attempts:
        try:
            say(f"Submitting via Program.rpc ({label})")
            return await rpc_fn(payload, ctx=ctx)
        except Exception as e:
            warn(f"Program.rpc {label} failed: {e}")
    return None

async def call_via_methods(program: Program, ix_name: str, accounts: dict, params_exact_obj: dict):
    methods_builder, chosen_method, _ = resolve_methods_builder(program, ix_name)
    if not methods_builder:
        warn("No Program.methods builder resolved"); return None
    acc_snake = to_snake_keys(accounts)
    snake = deep_snake(params_exact_obj)
    camel = params_exact_obj
    attempts = [
        ("wrapped/snake", {"params": snake}),
        ("naked/snake",   snake),
        ("wrapped/camel", {"params": camel}),
        ("naked/camel",   camel),
    ]
    for label, p in attempts:
        try:
            say(f"Submitting via Program.methods ({label})")
            mb = methods_builder(p).accounts(acc_snake) if callable(methods_builder) else methods_builder.accounts(acc_snake)
            sig = await mb.rpc()
            return sig
        except Exception as e:
            warn(f"Program.methods {label} failed: {e}")
    return None

# =========================
# RAW simulate & send with rotation/backoff
# =========================
async def simulate_and_send_raw(kp: Keypair,
                                idl_path: Path,
                                ix_name: str,
                                params_typed: Dict[str, Tuple[str, Any]],
                                accounts_camel: Dict[str, Pubkey],
                                endpoints: List[str],
                                start_idx: int = 0) -> Optional[str]:
    async def build_and_simulate(url: str):
        client = await new_client(url)
        try:
            ix = build_raw_instruction(idl_path, ix_name, params_typed, accounts_camel)
            bh = await client.get_latest_blockhash()
            tmp_tx = Transaction(fee_payer=kp.pubkey(), recent_blockhash=bh.value.blockhash)
            for b in compute_budget_ixs(): tmp_tx.add(b)
            tmp_tx.add(ix)
            sim = await client.simulate_transaction(tmp_tx, sig_verify=False)
            return client, ix, sim
        except Exception:
            await client.close()
            raise

    idx, (client, ix, sim) = await rpc_call_with_rotation(
        lambda url: build_and_simulate(url),
        endpoints=endpoints,
        start_idx=start_idx,
        attempts_per_endpoint=2,
        sleep_base=0.35
    )
    val = getattr(sim, "value", None)
    if val and getattr(val, "logs", None):
        info("raw simulate logs:"); [print(x) for x in val.logs]
    err_val = getattr(val, "err", None)
    if err_val:
        warn(f"raw simulate err: {err_val}")

    async def send_on(url: str):
        c = client if url == endpoints[idx] else await new_client(url)
        try:
            recent = await c.get_latest_blockhash()
            tx = Transaction(fee_payer=kp.pubkey(), recent_blockhash=recent.value.blockhash)
            for b in compute_budget_ixs(): tx.add(b)
            tx.add(ix)
            sig = await c.send_transaction(tx, kp, opts=TxOpts(skip_preflight=False, preflight_commitment=Processed))
            await c.confirm_transaction(sig.value, commitment=Confirmed)
            if c is not client: await c.close()
            return sig.value
        except Exception:
            if c is not client: await c.close()
            raise
    try:
        sig = await send_on(endpoints[idx]); await client.close(); return sig
    except Exception as e:
        warn(f"raw send error @ {endpoints[idx]}: {e!r}"); await client.close()
    for r in range(1, len(endpoints)):
        j = (idx + r) % len(endpoints)
        try:
            _, sig_val = await rpc_call_with_rotation(lambda url: send_on(url), endpoints=endpoints, start_idx=j, attempts_per_endpoint=1)
            return sig_val
        except Exception as e:
            warn(f"raw send error @ {endpoints[j]}: {e!r}")
    return None

# =========================
# Probe (side index × ATA mint)
#  - IMPORTANT UPDATE: positionRequestAta must be ATA(owner = positionRequest PDA, mint = inputMint)
# =========================
def build_accounts_camel_variant(owner: Pubkey,
                                 pool: Pubkey,
                                 custody_sol: Pubkey,
                                 custody_usdc: Pubkey,
                                 position: Pubkey,
                                 position_request: Pubkey,
                                 input_mint: Pubkey,
                                 ata_mode: str) -> Dict[str, Pubkey]:
    """
    ata_mode:
      - "request": keep positionRequestAta owner = positionRequest, mint = input_mint (recommended)
      - "position": owner = positionRequest, mint = position (less common, but probed)
    """
    mint_for_pr_ata = input_mint if ata_mode == "request" else position
    return {
        "owner": owner,
        "pool": pool,
        "custody": custody_sol,
        "collateralCustody": custody_usdc,
        "position": position,
        "positionRequest": position_request,
        "fundingAccount": derive_ata(owner, input_mint),
        "perpetuals": derive_perpetuals_pda(),
        "positionRequestAta": derive_ata(position_request, mint_for_pr_ata),  # <— UPDATED per Jupiter docs
        "inputMint": input_mint,
        "referral": owner,
        "tokenProgram": TOKEN_PROGRAM,
        "associatedTokenProgram": ASSOCIATED_TOKEN_PROGRAM,
        "systemProgram": SYSTEM_PROGRAM,
        "eventAuthority": derive_event_authority(),
        "program": PERPS_PROGRAM_ID,
    }

async def probe_and_send(kp: Keypair,
                         idl_path: Path,
                         ix_name: str,
                         base_params_typed: Dict[str, Tuple[str, Any]],
                         owner: Pubkey, pool: Pubkey,
                         custody_sol: Pubkey, custody_usdc: Pubkey,
                         position: Pubkey, position_request: Pubkey,
                         input_mint: Pubkey,
                         endpoints: List[str],
                         start_idx: int = 0) -> Optional[str]:
    side_field = next((k for k in base_params_typed.keys() if k.lower() == "side"), "side")
    for idx_val in (0, 1):
        params_try = dict(base_params_typed)
        if side_field in params_try and isinstance(params_try[side_field], tuple):
            kind, _ = params_try[side_field]
            params_try[side_field] = (kind, idx_val)
        for ata_mode in ("request", "position"):
            say(f"Probe variant: side_index={idx_val} ata_mint={ata_mode}")
            accounts_try = build_accounts_camel_variant(owner, pool, custody_sol, custody_usdc,
                                                        position, position_request, input_mint, ata_mode)
            sig = await simulate_and_send_raw(kp, idl_path, ix_name, params_try, accounts_try, endpoints, start_idx=start_idx)
            if sig:
                info(f"Probe success with side_index={idx_val}, ata_mint={ata_mode}")
                return sig
            warn(f"Probe variant failed: side={idx_val}, ata={ata_mode}")
    return None

# =========================
# Main action
# =========================
async def open_long_sol_with_usdc(endpoints: List[str],
                                  kp: Keypair,
                                  idl: Idl,
                                  size_usd_6dp: int,
                                  collateral_atoms: int,
                                  max_price_usd_6dp: int,
                                  dry_run: bool=False) -> str:
    say("Connecting program + provider")
    idx, client = await rpc_call_with_rotation(lambda url: new_client(url), endpoints=endpoints, attempts_per_endpoint=1)
    wallet   = Wallet(kp)
    provider = Provider(client, wallet)
    program  = Program(idl, PERPS_PROGRAM_ID, provider)
    done("program bound")

    owner = kp.pubkey()

    # Balances
    sol, usdc, _, _ = await print_wallet_balances(client, owner)

    # Preflight checks
    say("Preflight: SOL fee/rent check")
    lamports = int(sol * LAMPORTS_PER_SOL)
    info(f"have {lamports} lamports ({sol:.9f} SOL)  need ≥ {MIN_SOL_LAMPORTS} lamports ({MIN_SOL_LAMPORTS / LAMPORTS_PER_SOL:.9f} SOL)")
    if lamports < MIN_SOL_LAMPORTS:
        await client.close(); raise SystemExit("❌ Not enough SOL for fees/rent.")
    done("fee/rent OK")

    say("Preflight: USDC collateral check")
    need_usdc = collateral_atoms / (10 ** USDC_DECIMALS)
    info(f"have {usdc:.6f} USDC   need {need_usdc:.6f} USDC")
    if need_usdc > 0 and usdc + 1e-9 < need_usdc:
        await client.close(); raise SystemExit("❌ Not enough USDC collateral.")
    done("collateral OK")

    # PDAs
    say("Deriving PDAs & choosing instruction")
    position         = derive_position_pda(owner, POOL, CUSTODY_SOL, CUSTODY_USDC)
    counter          = int(time.time())
    position_request = derive_position_request_pda(position, counter)

    idl_json = _load_idl_json(IDL_PATH)
    ix_name = None
    for cand in ("createIncreasePositionMarketRequest", "create_increase_position_market_request", "createPositionRequest"):
        if _find_ix_json(idl_json, cand): ix_name = cand; break
    if not ix_name:
        names = [ix.name for ix in program.idl.instructions]
        for nm in names:
            l = nm.lower()
            if "increase" in l and "position" in l and "request" in l:
                ix_name = nm; break
    if not ix_name:
        await client.close(); raise SystemExit("❌ Could not find increase position request instruction in IDL.")
    info(f"instruction: {ix_name}")

    d(f"owner           : {owner}")
    d(f"pool            : {POOL}")
    d(f"custody (SOL)   : {CUSTODY_SOL}")
    d(f"custody (USDC)  : {CUSTODY_USDC}")
    d(f"position PDA    : {position}")
    d(f"positionRequest : {position_request}")
    done("PDAs ready")

    # Params from IDL JSON
    params_typed = build_params_from_idl_json(IDL_PATH, ix_name, size_usd_6dp, collateral_atoms, max_price_usd_6dp, counter_value=counter)
    binder_params_obj: Dict[str, Any] = {}
    for k, (kind, val) in params_typed.items():
        binder_params_obj[k] = {"Long": {}} if kind == "enum_index" and int(val) == 0 else ({"Short": {}} if kind == "enum_index" else val)

    # Accounts (UPDATED: positionRequestAta = ATA(owner = PositionRequest PDA, mint = inputMint (USDC)))
    accounts_camel = {
        "owner": owner,
        "pool": POOL,
        "custody": CUSTODY_SOL,
        "collateralCustody": CUSTODY_USDC,
        "position": position,
        "positionRequest": position_request,
        "fundingAccount": derive_ata(owner, USDC_MINT),                 # owner's USDC ATA
        "perpetuals": derive_perpetuals_pda(),
        "positionRequestAta": derive_ata(position_request, USDC_MINT),  # <— UPDATED per Jupiter docs
        "inputMint": USDC_MINT,
        "referral": owner,
        "tokenProgram": TOKEN_PROGRAM,
        "associatedTokenProgram": ASSOCIATED_TOKEN_PROGRAM,
        "systemProgram": SYSTEM_PROGRAM,
        "eventAuthority": derive_event_authority(),
        "program": PERPS_PROGRAM_ID,
    }

    say("Dumping params & accounts")
    info("params (from IDL JSON):"); print(json.dumps({k: (v[1] if isinstance(v, tuple) else v) for k,v in params_typed.items()}, indent=2))
    info("accounts (camel):");        print(json.dumps({k: str(v) for k, v in accounts_camel.items()}, indent=2))
    done("dumped")

    if dry_run:
        await client.close(); warn("dry-run enabled — not sending tx"); return "dry-run"

    # Binder first (may be incompatible; harmless to try once)
    sig = await call_with_param_styles(program, ix_name, accounts_camel, binder_params_obj)
    if not sig:
        sig = await call_via_methods(program, ix_name, accounts_camel, binder_params_obj)

    # RAW path with rotation/backoff
    if not sig:
        say("Falling back to RAW Anchor send …")
        sig = await simulate_and_send_raw(kp, IDL_PATH, ix_name, params_typed, accounts_camel, endpoints, start_idx=idx)

    # PROBE if still failing (side index × ATA mint variant)
    if not sig:
        say("All direct attempts failed — probing side/ATA variants")
        sig = await probe_and_send(kp, IDL_PATH, ix_name, params_typed,
                                   owner, POOL, CUSTODY_SOL, CUSTODY_USDC,
                                   position, position_request, USDC_MINT,
                                   endpoints, start_idx=idx)

    await client.close()

    if not sig:
        raise SystemExit("❌ All strategies failed (binder, raw, probe). See logs for details.")
    done(f"submitted → {sig}")
    info(f"PositionRequest PDA: {str(position_request)}"); info(f"Position PDA       : {str(position)}")
    return sig

# =========================
# CLI / Entrypoint
# =========================
def parse_args():
    p = argparse.ArgumentParser(description="Open a Jupiter Perps LONG SOL with USDC collateral (Market)")
    p.add_argument("--size-usd",        type=float, default=5.0)
    p.add_argument("--collateral-usdc", type=float, default=2.0)
    p.add_argument("--max-price",       type=float, default=1000.0)
    p.add_argument("--signer-file",     type=str,   default=None)
    p.add_argument("--force-idl-fetch", action="store_true")  # reserved
    p.add_argument("--dry-run",         action="store_true")
    p.add_argument("--debug",           action="store_true")
    return p.parse_args()

def to_6dp(n: float) -> int:        return int(round(n * 1_000_000))
def to_usdc_atoms(n: float) -> int: return int(round(n * 1_000_000))

async def _amain():
    global DEBUG
    args = parse_args()
    DEBUG = bool(args.debug or os.getenv("DEBUG") == "1")

    endpoints = load_endpoints()
    kp, pub = resolve_signer(args)
    idl = await ensure_idl()

    size_6 = to_6dp(args.size_usd)
    coll_6 = to_usdc_atoms(args.collateral_usdc)
    maxp_6 = to_6dp(args.max_price)

    say("Preparing order parameters")
    info(f"Action    : LONG SOL (market)")
    info(f"Size USD  : {args.size_usd} (6dp={size_6})")
    info(f"Collateral: {args.collateral_usdc} USDC (atoms={coll_6})")
    info(f"Max price : {args.max_price} USD (6dp={maxp_6})")
    done("params ready")

    await open_long_sol_with_usdc(
        endpoints=endpoints,
        kp=kp,
        idl=idl,
        size_usd_6dp=size_6,
        collateral_atoms=coll_6,
        max_price_usd_6dp=maxp_6,
        dry_run=bool(args.dry_run),
    )

if __name__ == "__main__":
    asyncio.run(_amain())
