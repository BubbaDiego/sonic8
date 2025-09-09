#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Open a Jupiter Perps LONG SOL position with USDC collateral (Market).

This version:
- Reads signer from a simple signer.txt at project root (default C:\\sonic5\\signer.txt)
- Supports mnemonic (BIP-39 -> SLIP-0010 ed25519) or secret_b64
- Prints each step BEFORE it runs (unicode icons)
- Robust RPC probe (timings + reasons)
- Aborts if derived pubkey != expected address
- Loud debug: balances, PDAs, IDL, accounts JSON, simulation logs
- IDL-driven params via RAW JSON (no AnchorPy IDL assumptions)
- Invocation ladder:
    • Program.rpc[...] (ctx with snake_case accounts; tries snake/camel wrapped/naked)
    • Program.methods.<name>(args).accounts(...).rpc()
    • RAW Anchor send (sighash + Borsh) with preflight simulation

signer.txt examples:

# Mnemonic mode
address=V8iveiirFvX7m7psPHWBJW85xPk1ZB6U4Ep9GUV2THW
mnemonic=word1 word2 ... word24
mnemonic_passphrase=
derivation_path=m/44'/501'/0'/0'

# Base64 secret mode (32/64 raw bytes, or base64 of "[12,34,...]" JSON keypair text)
address=V8iveiirFvX7m7psPHWBJW85xPk1ZB6U4Ep9GUV2THW
secret_b64=PASTE_BASE64_HERE
"""

import os, json, base64, argparse, asyncio, time, hmac, hashlib, unicodedata, struct
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
from anchorpy import Provider, Wallet, Program, Idl, Context

try:
    from borsh_construct import U8, U64
except Exception:
    U8 = U64 = None  # we’ll surface a friendly error if RAW path is needed without this dep

# =========================
# HARDCODED TEST SIGNER (optional)
# =========================
HARDCODE_SECRET_B64 = ""
HARDCODE_EXPECTED_PUBKEY = ""

# =========================
# PROJECT ROOT & DEFAULT SIGNER FILE
# =========================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SIGNER_FILE = PROJECT_ROOT / "signer.txt"

# =========================
# CHAIN / PROGRAM CONSTANTS
# =========================
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
MIN_SOL_LAMPORTS = int(os.getenv("MIN_SOL_LAMPORTS", "10000000"))  # 0.01 SOL default

RPC_FALLBACKS = [
    "https://api.mainnet-beta.solana.com",
    "https://rpc.ankr.com/solana",
]

DEBUG = True

# ---------- logging ----------
def say(step: str): print(f"\n🟠 {step} …", flush=True)
def done(msg: str = "done"): print(f"   ✅ {msg}", flush=True)
def info(msg: str): print(f"   ℹ️  {msg}", flush=True)
def warn(msg: str): print(f"   ⚠️  {msg}", flush=True)
def err(msg: str): print(f"   ❌ {msg}", flush=True)
def d(msg: str):
    if DEBUG: print(f"   🐛 {msg}", flush=True)
def log(msg: str): print(msg, flush=True)

# ---------- signer file ----------
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

# ---------- env / rpc ----------
def load_env() -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str], List[str], Optional[str]]:
    say("Loading environment (.env)")
    load_dotenv(override=True)
    rpc_url   = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")
    secret_b4 = os.getenv("WALLET_SECRET_BASELINE") or os.getenv("WALLET_SECRET_BASE64") or os.getenv("MNEMONIC_BASELINE") or os.getenv("MNEMONIC_BASE64")
    mnemonic  = os.getenv("MNEMONIC")
    mpass     = os.getenv("MNEMONIC_PASSPHRASE", "")
    dpath     = os.getenv("DERIVATION_PATH", "m/44'/501'/0'/0'")
    signer_file_env = os.getenv("SIGNER_FILE")
    extra: List[str] = []
    for k in ("RPC_LIST", "QUICKNODE_URL", "TRITON_URL", "HELIUS_URL"):
        v = os.getenv(k)
        if v:
            if k == "RPC_LIST": extra += [x.strip() for x in v.split(",") if x.strip()]
            else: extra.append(v.strip())
    info(f"RPC_URL={rpc_url}")
    d(f"WALLET_SECRET_BASE64={'set' if os.getenv('WALLET_SECRET_BASE64') else 'unset'} | MNEMONIC={'set' if mnemonic else 'unset'} | SIGNER_FILE={signer_file_env or 'unset'}")
    done("env loaded")
    return rpc_url, secret_b4, mnemonic, mpass, dpath, extra, signer_file_env

async def probe_rpc(url: str, timeout_sec: float = 3.5) -> Tuple[bool, str, float]:
    t0 = time.perf_counter()
    try:
        c = AsyncClient(url, commitment=Confirmed)
        ver = await asyncio.wait_for(c.get_version(), timeout=timeout_sec)
        await c.close()
        dt = (time.perf_counter() - t0) * 1000.0
        if ver and ver.value: return True, "ok", dt
        return False, "empty version", dt
    except Exception as e:
        dt = (time.perf_counter() - t0) * 1000.0
        return False, str(e), dt

async def choose_working_rpc(primary: str, extras: List[str]) -> str:
    say("Probing RPC endpoints")
    seen, cand = set(), []
    def add(u: Optional[str]):
        if u:
            u = u.strip()
            if u and u not in seen: seen.add(u); cand.append(u)
    add(primary)
    for x in extras: add(x)
    for x in RPC_FALLBACKS: add(x)
    if not cand: err("No RPC candidates"); raise SystemExit("No RPC provided. Set RPC_URL or --rpc.")
    for i, url in enumerate(cand, 1):
        info(f"🔌 [{i}/{len(cand)}] {url}")
        ok, reason, ms = await probe_rpc(url)
        if ok: done(f"RPC OK ({ms:.0f} ms) → {url}"); return url
        else: warn(f"RPC failed ({ms:.0f} ms) :: {reason}")
    err("No RPC reachable. Check internet/DNS/VPN or set a provider URL.")
    raise SystemExit("No RPC reachable.")

# ---------- BIP-39 -> ed25519 ----------
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
        num_str  = p[:-1] if p.endswith("'") else p
        idx = int(num_str, 10)
        if idx < 0 or idx >= 0x80000000: raise ValueError(f"Invalid index: {p}")
        idx |= 0x80000000; out.append(idx)
    return out

def keypair_from_mnemonic(mnemonic: str, passphrase: str = "", path: str = "m/44'/501'/0'/0'") -> Keypair:
    seed = _mnemonic_to_seed(mnemonic, passphrase)
    k, c = _slip10_ed25519_master(seed)
    for i in _parse_path(path): k, c = _slip10_ed25519_ckd_priv(k, c, i)
    return Keypair.from_seed(k)

# ---------- base64 secret loader ----------
def keypair_from_b64(secret_b64: str) -> Keypair:
    try: raw = base64.b64decode(secret_b64)
    except Exception as e: raise SystemExit(f"❌ Secret is not valid base64: {e}")
    try:
        if raw and raw[:1] == b"[" and raw[-1:] == b"]":
            arr = json.loads(raw.decode("utf-8")); b = bytes(arr)
            if len(b) == 64: return Keypair.from_bytes(b)
            raise SystemExit(f"❌ Decoded JSON keypair bytes={len(b)}; expected 64.")
    except Exception: pass
    n = len(raw)
    if n == 64: return Keypair.from_bytes(raw)
    if n == 32: return Keypair.from_seed(raw)
    raise SystemExit(f"❌ Unsupported secret length: {n}. Expected 32 or 64, or base64('[..]').")

# ---------- resolve signer ----------
def resolve_signer(args, env_secret_b64, env_mnemonic, env_mnemonic_pass, env_deriv_path, signer_file_env) -> Tuple[Keypair, str, str]:
    say("Resolving signer")
    signer_file: Optional[Path] = None
    if getattr(args, "signer_file", None): signer_file = Path(args.signer_file).resolve()
    elif signer_file_env:                  signer_file = Path(signer_file_env).resolve()
    elif DEFAULT_SIGNER_FILE.exists():     signer_file = DEFAULT_SIGNER_FILE
    if signer_file and signer_file.exists():
        info(f"Using SIGNER FILE: {signer_file}")
        kv = _parse_signer_file(signer_file)
        addr_expect = kv.get("address", "") or kv.get("expected_pubkey", "")
        if "secret_b64" in kv:
            kp  = keypair_from_b64(kv["secret_b64"]); pub = str(kp.pubkey())
            done(f"pubkey {pub} (file: secret_b64)")
            if addr_expect and addr_expect.strip() != pub: err("Derived pubkey != address from signer file"); raise SystemExit(f"expected {addr_expect} but got {pub}")
            return kp, pub, f"FILE:{signer_file.name}"
        if "mnemonic" in kv or any(k.startswith("mnemonic") for k in kv.keys()):
            phrase = kv.get("mnemonic", ""); mpass = kv.get("mnemonic_passphrase", ""); dpath = kv.get("derivation_path", "m/44'/501'/0'/0'")
            if not phrase: err("signer file has no mnemonic"); raise SystemExit("Add mnemonic=... to signer.txt")
            kp  = keypair_from_mnemonic(phrase, mpass or "", dpath); pub = str(kp.pubkey())
            done(f"pubkey {pub} (file: mnemonic, path {dpath})")
            if addr_expect and addr_expect.strip() != pub: err("Derived pubkey != address from signer file"); raise SystemExit(f"expected {addr_expect} but got {pub}")
            return kp, pub, f"FILE:{signer_file.name}"
        err("signer file missing 'secret_b64' or 'mnemonic'"); raise SystemExit("Add secret_b64=... OR mnemonic=... to signer.txt")
    if HARDCODE_SECRET_B64:
        info("Using HARDCODE secret")
        kp  = keypair_from_b64(HARDCODE_SECRET_B64.strip()); pub = str(kp.pubkey())
        done(f"pubkey {pub}")
        if HARDCODE_EXPECTED_PUBKEY and HARDCODE_EXPECTED_PUBKEY.strip() != pub: err("Derived pubkey != HARDCODE_EXPECTED_PUBKEY"); raise SystemExit(f"expected {HARDCODE_EXPECTED_PUBKEY} but got {pub}")
        return kp, pub, "HARDCODE"
    if getattr(args, "secret_b64", None):
        info("Using CLI --secret-b64")
        kp  = keypair_from_b64(args.secret_b64.strip()); pub = str(kp.pubkey())
        done(f"pubkey {pub}")
        if getattr(args, "expected_pubkey", None) and args.expected_pubkey.strip() != pub: err("Derived pubkey != --expected-pubkey"); raise SystemExit(f"expected {args.expected_pubkey} but got {pub}")
        return kp, pub, "CLI:secret_b64"
    if getattr(args, "secret_b64_file", None):
        info("Using CLI --secret-b64-file")
        with open(args.secret_b64_file, "r", encoding="utf-8") as fh: b64 = fh.read().strip()
        kp  = keypair_from_b64(b64); pub = str(kp.pubkey())
        done(f"pubkey {pub}")
        if getattr(args, "expected_pubkey", None) and args.expected_pubkey.strip() != pub: err("Derived pubkey != --expected-pubkey"); raise SystemExit(f"expected {args.expected_pubkey} but got {pub}")
        return kp, pub, "CLI:secret_b64_file"
    if getattr(args, "mnemonic", None) or getattr(args, "mnemonic_file", None):
        info("Using CLI mnemonic")
        if getattr(args, "mnemonic_file", None):
            with open(args.mnemonic_file, "r", encoding="utf-8") as fh: phrase = fh.read().strip()
        else:
            phrase = args.mnemonic
        mpass = getattr(args, "mnemonic_passphrase", "") or ""; dpath = getattr(args, "derivation_path", "m/44'/501'/0'/0'")
        kp  = keypair_from_mnemonic(phrase, mpass, dpath); pub = str(kp.pubkey())
        done(f"pubkey {pub} (path {dpath})")
        if getattr(args, "expected_pubkey", None) and args.expected_pubkey.strip() != pub: err("Derived pubkey != --expected-pubkey"); raise SystemExit(f"expected {args.expected_pubkey} but got {pub}")
        return kp, pub, "CLI:mnemonic"
    err("No signer provided"); raise SystemExit("Provide signer via signer.txt, HARDCODE_SECRET_B64, or CLI.")

# ---------- IDL ----------
async def fetch_idl_onchain(rpc_url: str) -> Optional[Idl]:
    client = AsyncClient(rpc_url, commitment=Confirmed); provider = Provider(client, Wallet(Keypair()))
    try: idl = await Program.fetch_idl(PERPS_PROGRAM_ID, provider); await client.close(); return idl
    except Exception as e: d(f"IDL fetch failed: {e}"); await client.close(); return None

def save_idl_to_path(idl: Idl, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f: json.dump(idl.to_json(), f, indent=2)

async def ensure_idl(rpc_url: str, path: Path, force_refresh: bool=False) -> Idl:
    say("Ensuring IDL")
    if force_refresh and path.exists():
        try: path.unlink(); info(f"Removed stale IDL at {path}")
        except Exception as e: warn(f"Could not remove IDL: {e}")
    if path.exists():
        info(f"Loading IDL from {path}")
        text = path.read_text(encoding="utf-8")
        try: idl = Idl.from_json(text)
        except: idl = Idl.from_json(json.loads(text))
        done("IDL loaded from disk"); return idl
    info("Fetching IDL from chain")
    idl = await fetch_idl_onchain(rpc_url)
    if idl is None: err("Failed to fetch IDL"); raise SystemExit(f"Place the IDL at {path}")
    save_idl_to_path(idl, path); done(f"IDL saved to {path}"); return idl

# ---------- PDAs ----------
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

# ---------- RAW IDL JSON helpers ----------
def _load_idl_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"❌ Failed to read IDL JSON at {path}: {e}")

def _find_ix_json(idl_json: dict, ix_name: str) -> Optional[dict]:
    for ix in idl_json.get("instructions", []):
        if ix.get("name") == ix_name:
            return ix
    snake = _camel_to_snake(ix_name)
    for ix in idl_json.get("instructions", []):
        if ix.get("name") == snake:
            return ix
    return None

def _find_type_json(idl_json: dict, name: str) -> Optional[dict]:
    for t in idl_json.get("types", []) or []:
        if t.get("name") == name:
            return t
    return None

def _enum_json_variant_index(idl_json: dict, enum_name: str, want: str) -> int:
    t = _find_type_json(idl_json, enum_name)
    want_low = (want or "").lower()
    if t and t.get("type", {}).get("kind") == "enum":
        for i, v in enumerate(t["type"].get("variants", [])):
            nm = v.get("name","")
            if nm.lower() == want_low:
                return i
        return 0
    return 0

def build_params_from_idl_json(idl_path: Path,
                               ix_name: str,
                               size_usd_6dp: int,
                               collateral_atoms: int,
                               max_price_usd_6dp: int,
                               counter_value: int | None = None) -> Dict[str, Tuple[str, Any]]:
    j = _load_idl_json(idl_path)
    ix = _find_ix_json(j, ix_name)
    if not ix:
        raise SystemExit(f"❌ IDL JSON has no instruction named {ix_name}")
    args = ix.get("args", [])
    if not args:
        info("IDL JSON shows no args for this instruction.")
        return {}
    arg0 = args[0]
    t = arg0.get("type", {})
    defined = t.get("defined")
    fields = None
    if defined:
        type_def = _find_type_json(j, defined)
        if not type_def:
            raise SystemExit(f"❌ IDL JSON missing type definition {defined}")
        ty = type_def.get("type", {})
        if ty.get("kind") != "struct":
            raise SystemExit(f"❌ IDL JSON type {defined} is not a struct")
        fields = ty.get("fields", [])
        info(f"IDL JSON params '{arg0.get('name')}' → defined type '{defined}' fields: {[f['name'] for f in fields]}")
    else:
        ty = t
        fields = ty.get("fields", [])
        if ty.get("kind") != "struct":
            info("IDL JSON arg0 not a defined struct; will try robust aliases.")

    params: Dict[str, Tuple[str, Any]] = {}
    if fields:
        for f in fields:
            nm = f.get("name")
            nm_low = nm.lower()
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

# ---------- binder method resolution helpers ----------
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

# ---------- tiny name helpers (needed by resolve_* functions) ----------
def _camel_to_snake(name: str) -> str:
    out = []
    for ch in name:
        out.append("_" + ch.lower() if ch.isupper() else ch)
    s = "".join(out)
    return s[1:] if s.startswith("_") else s

def _best_key(keys: list[str], target: str) -> Optional[str]:
    """
    Pick the best key from `keys` that matches `target`:
    1) exact match
    2) snake_case match
    3) fuzzy: prefer entries containing 'increase','position','request','market' with
       at least 'position' & 'request' present.
    """
    if target in keys:
        return target
    snake = _camel_to_snake(target)
    if snake in keys:
        return snake
    want = ["increase", "position", "request", "market"]
    ranked = []
    for k in keys:
        l = k.lower()
        if "position" in l and "request" in l:
            ranked.append((sum(w in l for w in want), k))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked else None


# ---------- tiny name helpers (needed by resolve_* functions) ----------
def _camel_to_snake(name: str) -> str:
    out = []
    for ch in name:
        out.append("_" + ch.lower() if ch.isupper() else ch)
    s = "".join(out)
    return s[1:] if s.startswith("_") else s

def _best_key(keys: list[str], target: str) -> Optional[str]:
    """
    Pick the best key from `keys` that matches `target`:
    1) exact match
    2) snake_case match
    3) fuzzy: prefer entries containing 'increase','position','request','market' with
       at least 'position' & 'request' present.
    """
    if target in keys:
        return target
    snake = _camel_to_snake(target)
    if snake in keys:
        return snake
    want = ["increase", "position", "request", "market"]
    ranked = []
    for k in keys:
        l = k.lower()
        if "position" in l and "request" in l:
            ranked.append((sum(w in l for w in want), k))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked else None


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

# ---------- RAW ENCODING (Anchor sighash + Borsh) ----------
def _anchor_sighash(ix_name_snake: str) -> bytes:
    seed = f"global:{ix_name_snake}".encode("utf-8")
    return hashlib.sha256(seed).digest()[:8]

def _ix_name_for_hash(idl_json: dict, ix_name: str) -> str:
    ix = _find_ix_json(idl_json, ix_name)
    if ix: return ix["name"]
    return _camel_to_snake(ix_name)

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

def build_raw_instruction(idl_path: Path,
                          ix_name: str,
                          params_typed: Dict[str, Tuple[str, Any]],
                          accounts_camel: Dict[str, Pubkey]) -> Instruction:
    j = _load_idl_json(idl_path)
    ix_json = _find_ix_json(j, ix_name)
    if not ix_json:
        raise SystemExit(f"❌ IDL JSON has no instruction named {ix_name}")

    # Log the exact accounts (order + flags) the program expects
    req = [(a["name"], bool(a.get("isMut")), bool(a.get("isSigner"))) for a in ix_json.get("accounts", [])]
    info("IDL accounts (order, mut, signer): " + ", ".join([f"{n}(mut={m},signer={s})" for n,m,s in req]))

    # 1) sighash
    name_for_hash = _ix_name_for_hash(j, ix_name)
    sighash = _anchor_sighash(name_for_hash)

    # 2) params bytes
    arg0 = (ix_json.get("args") or [])[0]
    defined = (arg0.get("type") or {}).get("defined")
    if not defined:
        raise SystemExit("❌ IDL arg type is not 'defined' struct; raw encoder needs a named struct.")
    params_bytes = encode_params_borsh_from_typed(j, defined, params_typed)

    data = sighash + params_bytes

    # 3) accounts per IDL JSON order
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
        metas.append(AccountMeta(
            pubkey=cand,
            is_signer=bool(acc.get("isSigner")),
            is_writable=bool(acc.get("isMut")),
        ))
    return Instruction(program_id=PERPS_PROGRAM_ID, accounts=metas, data=data)

# ---------- snake-case helpers ----------
def to_snake_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Shallow: convert top-level keys of a dict from camelCase/PascalCase to snake_case.
    Values are left untouched (use deep_snake for nested structs).
    """
    out: Dict[str, Any] = {}
    for k, v in (d or {}).items():
        s = []
        for ch in str(k):
            s.append("_" + ch.lower() if ch.isupper() else ch)
        key = "".join(s)
        if key.startswith("_"):
            key = key[1:]
        out[key] = v
    return out

def deep_snake(x: Any) -> Any:
    """
    Deep: recursively convert dict keys to snake_case (lists traversed, primitives returned).
    """
    if isinstance(x, dict):
        y: Dict[str, Any] = {}
        for k, v in x.items():
            s = []
            for ch in str(k):
                s.append("_" + ch.lower() if ch.isupper() else ch)
            key = "".join(s)
            if key.startswith("_"):
                key = key[1:]
            y[key] = deep_snake(v)
        return y
    if isinstance(x, list):
        return [deep_snake(v) for v in x]
    return x


# ---------- RPC call attempts (returns None to fall through when all fail) ----------
async def call_with_param_styles(fn, ix_name: str, accounts: dict, params_exact_obj: dict, program: Program):
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
        say("Simulating (first variant)")
        first = attempts[0][1]
        sim = await program.simulate(ix_name, first if isinstance(first, dict) else {"params": first}, ctx=ctx)
        if getattr(sim, "value", None) and getattr(sim.value, "logs", None):
            info("simulation logs:"); [print(x) for x in sim.value.logs]
    except Exception as e:
        warn(f"simulate raised: {e}")

    for label, payload in attempts:
        try:
            say(f"Submitting via Program.rpc ({label})")
            return await fn(payload, ctx=ctx)
        except Exception as e:
            warn(f"Program.rpc {label} failed: {e}")
    return None

# ---------- Program.methods fallback ----------
async def call_via_methods(builder, ix_name: str, accounts: dict, params_exact_obj: dict, program: Program):
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
            if callable(builder):
                mb = builder(p).accounts(acc_snake)
            else:
                mb = builder.accounts(acc_snake)  # best-effort
            sig = await mb.rpc()
            return sig
        except Exception as e:
            warn(f"Program.methods {label} failed: {e}")
    return None

# ---------- Program.instruction RAW fallback (with simulation logs) ----------
async def call_via_instruction_raw(idl_path: Path,
                                   ix_name: str,
                                   params_typed: Dict[str, Tuple[str, Any]],
                                   accounts_camel: Dict[str, Pubkey],
                                   kp: Keypair,
                                   client: AsyncClient) -> Optional[str]:
    try:
        if U8 is None or U64 is None:
            raise SystemExit("❌ Missing dependency 'borsh-construct'. Run: pip install borsh-construct")

        say("Building raw Anchor instruction (sighash + borsh)")
        ix = build_raw_instruction(idl_path, ix_name, params_typed, accounts_camel)

        # Optional ComputeBudget (helps avoid CU/priority issues on busy RPCs)
        budget_ixs = []
        try:
            from solders.pubkey import Pubkey as _PK
            from solders.instruction import Instruction as _I
            COMPUTE_BUDGET = _PK.from_string("ComputeBudget111111111111111111111111111111")
            # setComputeUnitLimit(0x02) -> u32 limit
            budget_ixs.append(_I(COMPUTE_BUDGET, (), bytes([2]) + int(1_000_000).to_bytes(4, "little")))
            # setComputeUnitPrice(0x03) -> u64 microLamports
            budget_ixs.append(_I(COMPUTE_BUDGET, (), bytes([3]) + int(1_000).to_bytes(8, "little")))
        except Exception:
            warn("ComputeBudget not added (optional); proceeding without it")

        # ---- Preflight simulate with FRESH blockhash; retry once on BlockhashNotFound
        for attempt in (1, 2):
            bh = await client.get_latest_blockhash()
            tmp_tx = Transaction(fee_payer=kp.pubkey(), recent_blockhash=bh.value.blockhash)
            for b in budget_ixs: tmp_tx.add(b)
            tmp_tx.add(ix)
            sim = await client.simulate_transaction(tmp_tx, sig_verify=False)
            val = getattr(sim, "value", None)
            if val and getattr(val, "logs", None):
                info(f"raw simulate logs (attempt {attempt}):")
                for line in val.logs: print(line)
            err_val = getattr(val, "err", None)
            if not err_val:
                break
            msg = str(err_val)
            warn(f"raw simulate err (attempt {attempt}): {msg}")
            if "BlockhashNotFound" not in msg:
                break  # real program error surfaced; we’ll still try to send, but logs are what we need

        # ---- Send with NEW blockhash and confirm
        recent = await client.get_latest_blockhash()
        tx = Transaction(fee_payer=kp.pubkey(), recent_blockhash=recent.value.blockhash)
        for b in budget_ixs: tx.add(b)
        tx.add(ix)
        try:
            sig = await client.send_transaction(
                tx, kp, opts=TxOpts(skip_preflight=False, preflight_commitment=Processed)
            )
            await client.confirm_transaction(sig.value, commitment=Confirmed)
            return sig.value
        except Exception as e:
            # Print full RPC error payload if present
            warn(f"raw send error type={type(e).__name__} repr={repr(e)}")
            if hasattr(e, "args") and e.args:
                warn(f"RPC error detail: {e.args[0]}")
            return None

    except Exception as e:
        warn(f"raw instruction failed type={type(e).__name__} repr={repr(e)}")
        return None



# ---------- main action ----------
async def open_long_sol_with_usdc(rpc_url: str, kp: Keypair, idl: Idl, size_usd_6dp: int, collateral_atoms: int, max_price_usd_6dp: int, dry_run: bool=False) -> str:
    say("Connecting program + provider")
    client   = AsyncClient(rpc_url, commitment=Confirmed)
    wallet   = Wallet(kp)
    provider = Provider(client, wallet)
    program  = Program(idl, PERPS_PROGRAM_ID, provider)
    done("program bound")

    owner = kp.pubkey()

    # 1) balances
    sol, usdc, _, _ = await print_wallet_balances(client, owner)

    # 2) preflight: SOL
    say("Preflight: SOL fee/rent check")
    lamports = int(sol * LAMPORTS_PER_SOL)
    info(f"have {lamports} lamports ({sol:.9f} SOL)  need ≥ {MIN_SOL_LAMPORTS} lamports ({MIN_SOL_LAMPORTS / LAMPORTS_PER_SOL:.9f} SOL)")
    if lamports < MIN_SOL_LAMPORTS:
        await client.close(); err("Insufficient SOL for fees/rent"); raise SystemExit("Not enough SOL — top up and retry.")
    done("fee/rent OK")

    # 3) preflight: USDC
    say("Preflight: USDC collateral check")
    need_usdc = collateral_atoms / (10 ** USDC_DECIMALS)
    info(f"have {usdc:.6f} USDC   need {need_usdc:.6f} USDC")
    if need_usdc > 0 and usdc + 1e-9 < need_usdc:
        await client.close(); err("Insufficient USDC collateral"); raise SystemExit("Not enough USDC — deposit or reduce collateral amount.")
    done("collateral OK")

    # 4) PDAs & ix name
    say("Deriving PDAs & choosing instruction")
    position         = derive_position_pda(owner, POOL, CUSTODY_SOL, CUSTODY_USDC)
    counter          = int(time.time())  # also used in params
    position_request = derive_position_request_pda(position, counter)

    # choose instruction name (prefer market increase)
    idl_json = json.loads(IDL_PATH.read_text(encoding="utf-8")) if IDL_PATH.exists() else {}
    ix_name = None
    for cand in ("createIncreasePositionMarketRequest", "create_increase_position_market_request", "createPositionRequest"):
        if _find_ix_json(idl_json, cand):
            ix_name = cand; break
    if not ix_name:
        names = [ix.name for ix in program.idl.instructions]
        for nm in names:
            low = nm.lower()
            if "increase" in low and "position" in low and "request" in low:
                ix_name = nm; break
    if not ix_name:
        await client.close(); raise SystemExit("❌ Could not find an increase position market request instruction in IDL.")
    info(f"instruction: {ix_name}")

    d(f"owner           : {owner}")
    d(f"pool            : {POOL}")
    d(f"custody (SOL)   : {CUSTODY_SOL}")
    d(f"custody (USDC)  : {CUSTODY_USDC}")
    d(f"position PDA    : {position}")
    d(f"positionRequest : {position_request}")
    done("PDAs ready")

    # 5) params from RAW IDL JSON (include real counter)
    params_typed = build_params_from_idl_json(IDL_PATH, ix_name, size_usd_6dp, collateral_atoms, max_price_usd_6dp, counter_value=counter)

    # Friendly object for binder attempts:
    binder_params_obj: Dict[str, Any] = {}
    for k, (kind, val) in params_typed.items():
        if kind == "enum_index":
            binder_params_obj[k] = {"Long": {}} if int(val) == 0 else {"Short": {}}
        else:
            binder_params_obj[k] = val

    # 6) accounts (camel) — IMPORTANT: positionRequestAta uses positionRequest as MINT
    accounts_camel = {
        "owner": owner,
        "pool": POOL,
        "custody": CUSTODY_SOL,
        "collateralCustody": CUSTODY_USDC,
        "position": position,
        "positionRequest": position_request,
        "fundingAccount": derive_ata(owner, USDC_MINT),            # owner's USDC ATA
        "perpetuals": derive_perpetuals_pda(),
        "positionRequestAta": derive_ata(owner, position_request), # <-- correct mint = positionRequest
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

    # 7) Try binder first
    rpc_fn, chosen_rpc, _ = resolve_rpc_call(program, ix_name)
    sig = None
    if rpc_fn:
        info(f"RPC method chosen: {chosen_rpc}")
        sig = await call_with_param_styles(rpc_fn, ix_name, accounts_camel, binder_params_obj, program)

    # 8) Program.methods fallback
    if not sig:
        methods_builder, chosen_method, _ = resolve_methods_builder(program, ix_name)
        if methods_builder:
            info(f"Methods builder chosen: {chosen_method}")
            sig = await call_via_methods(methods_builder, ix_name, accounts_camel, binder_params_obj, program)

    # 9) RAW instruction fallback
    if not sig:
        say("Falling back to RAW Anchor send …")
        sig = await call_via_instruction_raw(IDL_PATH, ix_name, params_typed, accounts_camel, kp, client)

    await client.close()

    if not sig:
        err("All invocation strategies failed.")
        raise SystemExit("No binder path accepted the arguments; raw fallback also failed (see logs).")

    done(f"submitted → {sig}")
    info(f"PositionRequest PDA: {str(position_request)}"); info(f"Position PDA       : {str(position)}")
    log("ℹ️ Keepers will fulfill the request if it passes all checks.")
    return sig

# ---------- balances helpers (re-add) ----------
async def fetch_spl_ui_balance(client: AsyncClient, owner: Pubkey, mint: Pubkey) -> Tuple[float, Pubkey, bool]:
    """
    Return (ui_amount, ata_pubkey, exists)
    """
    ata = derive_ata(owner, mint)
    acc_info = await client.get_account_info(ata)
    if acc_info.value is None:
        return 0.0, ata, False
    bal = await client.get_token_account_balance(ata)
    try:
        ui = float(bal.value.ui_amount_string or "0")
    except Exception:
        ui = 0.0
    return ui, ata, True

async def print_wallet_balances(client: AsyncClient, owner: Pubkey) -> Tuple[float, float, float, float]:
    """
    Log SOL + common SPL balances and return (sol, usdc, eth, btc) in UI units.
    """
    say("Fetching wallet balances")
    lamports = (await client.get_balance(owner)).value
    sol = lamports / LAMPORTS_PER_SOL

    usdc, usdc_ata, usdc_exists = await fetch_spl_ui_balance(client, owner, USDC_MINT)

    # Optional: if you don't track wETH/WBTC, you can keep these 0.0 or comment out.
    # They don't affect perps flow, but are useful for quick sanity.
    try:
        from solders.pubkey import Pubkey as _PK  # just to be safe in local scopes
        WETH_MINT_LOCAL = _PK.from_string("7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs")
        WBTC_MINT_LOCAL = _PK.from_string("9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E")
    except Exception:
        WETH_MINT_LOCAL = USDC_MINT
        WBTC_MINT_LOCAL = USDC_MINT

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


# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(description="Open a Jupiter Perps LONG SOL with USDC collateral (Market)")
    p.add_argument("--size-usd",        type=float, default=5.0)
    p.add_argument("--collateral-usdc", type=float, default=2.0)
    p.add_argument("--max-price",       type=float, default=1000.0)
    p.add_argument("--rpc",             type=str,   default=None)
    p.add_argument("--rpc-list",        type=str,   default="")
    p.add_argument("--signer-file",     type=str,   default=None)
    p.add_argument("--secret-b64",      type=str,   default=None)
    p.add_argument("--secret-b64-file", type=str,   default=None)
    p.add_argument("--mnemonic",        type=str,   default=None)
    p.add_argument("--mnemonic-file",   type=str,   default=None)
    p.add_argument("--mnemonic-passphrase", type=str, default="")
    p.add_argument("--derivation-path", type=str,   default="m/44'/501'/0'/0'")
    p.add_argument("--expected-pubkey", type=str,   default=None)
    p.add_argument("--force-idl-fetch", action="store_true")
    p.add_argument("--dry-run",         action="store_true")
    p.add_argument("--debug",           action="store_true")
    return p.parse_args()

def to_6dp(n: float) -> int:        return int(round(n * 1_000_000))
def to_usdc_atoms(n: float) -> int: return int(round(n * 1_000_000))

# ---------- main ----------
async def _amain():
    global DEBUG
    args = parse_args()
    DEBUG = bool(args.debug or os.getenv("DEBUG") == "1")

    rpc_env, env_secret, env_mnemonic, env_mpass, env_dpath, rpc_extra, signer_file_env = load_env()
    cli_rpc_list = [x.strip() for x in (args.rpc_list or "").split(",") if x.strip()]
    rpc_candidate = args.rpc or rpc_env
    rpc_url = await choose_working_rpc(rpc_candidate, cli_rpc_list + rpc_extra)

    kp, pub, src = resolve_signer(args, None, None, None, None, signer_file_env)

    idl = await ensure_idl(rpc_url, IDL_PATH, force_refresh=args.force_idl_fetch)

    size_6 = to_6dp(args.size_usd)
    coll_6 = to_usdc_atoms(args.collateral_usdc)
    maxp_6 = to_6dp(args.max_price)

    say("Preparing order parameters")
    info(f"Action    : LONG SOL (market)")
    info(f"Size USD  : {args.size_usd}  (6dp={size_6})")
    info(f"Collateral: {args.collateral_usdc} USDC  (atoms={coll_6})")
    info(f"Max price : {args.max_price} USD  (6dp={maxp_6})")
    done("params ready")

    await open_long_sol_with_usdc(
        rpc_url=rpc_url,
        kp=kp,
        idl=idl,
        size_usd_6dp=size_6,
        collateral_atoms=coll_6,
        max_price_usd_6dp=maxp_6,
        dry_run=bool(args.dry_run),
    )

if __name__ == "__main__":
    asyncio.run(_amain())
