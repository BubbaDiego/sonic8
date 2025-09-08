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
- Robust invocation:
    • Program.rpc[<name>] / Program.rpc.<name>  (with ctx=Context(accounts=snake_case_map))
    • Program.methods.<name>(args).accounts(...).rpc()
    • Program.instruction.<name>(args, accounts) + manual send (last resort)
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
from anchorpy import Provider, Wallet, Program, Idl, Context

# =========================
# HARDCODED TEST SIGNER  ⬇ (used only if signer file is absent)
# =========================
HARDCODE_SECRET_B64 = ""      # base64 of 32 seed, 64 secret, or base64('[..]')
HARDCODE_EXPECTED_PUBKEY = "" # optional guard: expected address

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
WETH_MINT = Pubkey.from_string(os.getenv("MINT_WETH", "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs"))
WBTC_MINT = Pubkey.from_string(os.getenv("MINT_WBTC", "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E"))

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

# ---------- kv signer file ----------
def _parse_signer_file(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    txt = path.read_text(encoding="utf-8").splitlines()
    for raw in txt:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
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
    secret_b4 = os.getenv("WALLET_SECRET_BASE64") or os.getenv("MNEMONIC_BASE64")
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
        if ver and ver.value:
            return True, "ok", dt
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
            if u and u not in seen:
                seen.add(u); cand.append(u)
    add(primary)
    for x in extras: add(x)
    for x in RPC_FALLBACKS: add(x)
    if not cand:
        err("No RPC candidates")
        raise SystemExit("No RPC provided. Set RPC_URL or --rpc.")
    for i, url in enumerate(cand, 1):
        info(f"🔌 [{i}/{len(cand)}] {url}")
        ok, reason, ms = await probe_rpc(url)
        if ok:
            done(f"RPC OK ({ms:.0f} ms) → {url}")
            return url
        else:
            warn(f"RPC failed ({ms:.0f} ms) :: {reason}")
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
    I = _hmac_sha512(b"ed25519 seed", seed)
    return I[:32], I[32:]

def _slip10_ed25519_ckd_priv(k_par: bytes, c_par: bytes, i: int) -> Tuple[bytes, bytes]:
    if i < 0x80000000:
        raise ValueError("ed25519 CKD requires hardened indices")
    data = b"\x00" + k_par + struct.pack(">L", i)
    I = _hmac_sha512(c_par, data)
    return I[:32], I[32:]

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
        idx |= 0x80000000
        out.append(idx)
    return out

def keypair_from_mnemonic(mnemonic: str, passphrase: str = "", path: str = "m/44'/501'/0'/0'") -> Keypair:
    seed = _mnemonic_to_seed(mnemonic, passphrase)
    k, c = _slip10_ed25519_master(seed)
    for i in _parse_path(path):
        k, c = _slip10_ed25519_ckd_priv(k, c, i)
    return Keypair.from_seed(k)

# ---------- base64 secret loader ----------
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
    raise SystemExit(f"❌ Unsupported secret length: {n}. Expected 32 (seed) or 64 (secret key), or base64('[..]').")

# ---------- resolve signer ----------
def resolve_signer(
    args,
    env_secret_b64: Optional[str],
    env_mnemonic: Optional[str],
    env_mnemonic_pass: Optional[str],
    env_deriv_path: Optional[str],
    signer_file_env: Optional[str],
) -> Tuple[Keypair, str, str]:
    say("Resolving signer")
    signer_file: Optional[Path] = None
    if getattr(args, "signer_file", None):
        signer_file = Path(args.signer_file).resolve()
    elif signer_file_env:
        signer_file = Path(signer_file_env).resolve()
    elif DEFAULT_SIGNER_FILE.exists():
        signer_file = DEFAULT_SIGNER_FILE

    if signer_file and signer_file.exists():
        info(f"Using SIGNER FILE: {signer_file}")
        kv = _parse_signer_file(signer_file)
        addr_expect = kv.get("address", "") or kv.get("expected_pubkey", "")
        if "secret_b64" in kv:
            kp  = keypair_from_b64(kv["secret_b64"])
            pub = str(kp.pubkey())
            done(f"pubkey {pub} (file: secret_b64)")
            if addr_expect and addr_expect.strip() != pub:
                err("Derived pubkey != address from signer file")
                raise SystemExit(f"expected {addr_expect} but got {pub}")
            return kp, pub, f"FILE:{signer_file.name}"
        if "mnemonic" in kv or any(k.startswith("mnemonic") for k in kv.keys()):
            phrase = kv.get("mnemonic", "")
            mpass  = kv.get("mnemonic_passphrase", "")
            dpath  = kv.get("derivation_path", "m/44'/501'/0'/0'")
            if not phrase:
                err("signer file has no mnemonic value")
                raise SystemExit("Add mnemonic=... to signer.txt")
            kp  = keypair_from_mnemonic(phrase, mpass or "", dpath)
            pub = str(kp.pubkey())
            done(f"pubkey {pub} (file: mnemonic, path {dpath})")
            if addr_expect and addr_expect.strip() != pub:
                err("Derived pubkey != address from signer file")
                raise SystemExit(f"expected {addr_expect} but got {pub}")
            return kp, pub, f"FILE:{signer_file.name}"
        err("signer file missing 'secret_b64' or 'mnemonic'")
        raise SystemExit("Add secret_b64=... OR mnemonic=... to signer.txt")

    if HARDCODE_SECRET_B64:
        info("Using HARDCODE secret")
        kp  = keypair_from_b64(HARDCODE_SECRET_B64.strip())
        pub = str(kp.pubkey())
        done(f"pubkey {pub}")
        if HARDCODE_EXPECTED_PUBKEY and HARDCODE_EXPECTED_PUBKEY.strip() != pub:
            err("Derived pubkey != HARDCODE_EXPECTED_PUBKEY")
            raise SystemExit(f"expected {HARDCODE_EXPECTED_PUBKEY} but got {pub}")
        return kp, pub, "HARDCODE"

    if getattr(args, "secret_b64", None):
        info("Using CLI --secret-b64")
        kp  = keypair_from_b64(args.secret_b64.strip())
        pub = str(kp.pubkey())
        done(f"pubkey {pub}")
        if getattr(args, "expected_pubkey", None) and args.expected_pubkey.strip() != pub:
            err("Derived pubkey != --expected-pubkey")
            raise SystemExit(f"expected {args.expected_pubkey} but got {pub}")
        return kp, pub, "CLI:secret_b64"

    if getattr(args, "secret_b64_file", None):
        info("Using CLI --secret-b64-file")
        with open(args.secret_b64_file, "r", encoding="utf-8") as fh:
            b64 = fh.read().strip()
        kp  = keypair_from_b64(b64)
        pub = str(kp.pubkey())
        done(f"pubkey {pub}")
        if getattr(args, "expected_pubkey", None) and args.expected_pubkey.strip() != pub:
            err("Derived pubkey != --expected-pubkey")
            raise SystemExit(f"expected {args.expected_pubkey} but got {pub}")
        return kp, pub, "CLI:secret_b64_file"

    if getattr(args, "mnemonic", None) or getattr(args, "mnemonic_file", None):
        info("Using CLI mnemonic")
        if getattr(args, "mnemonic_file", None):
            with open(args.mnemonic_file, "r", encoding="utf-8") as fh:
                phrase = fh.read().strip()
        else:
            phrase = args.mnemonic
        mpass = getattr(args, "mnemonic_passphrase", "") or ""
        dpath = getattr(args, "derivation_path", "m/44'/501'/0'/0'")
        kp  = keypair_from_mnemonic(phrase, mpass, dpath)
        pub = str(kp.pubkey())
        done(f"pubkey {pub} (path {dpath})")
        if getattr(args, "expected_pubkey", None) and args.expected_pubkey.strip() != pub:
            err("Derived pubkey != --expected-pubkey")
            raise SystemExit(f"expected {args.expected_pubkey} but got {pub}")
        return kp, pub, "CLI:mnemonic"

    if env_mnemonic:
        info("Using ENV MNEMONIC")
        kp  = keypair_from_mnemonic(env_mnemonic, env_mnemonic_pass or "", env_deriv_path or "m/44'/501'/0'/0'")
        pub = str(kp.pubkey())
        done(f"pubkey {pub}")
        if os.getenv("EXPECTED_PUBKEY") and os.getenv("EXPECTED_PUBKEY").strip() != pub:
            err("Derived pubkey != EXPECTED_PUBKEY")
            raise SystemExit(f"expected {os.getenv('EXPECTED_PUBKEY')} but got {pub}")
        return kp, pub, "ENV:MNEMONIC"

    if env_secret_b64:
        info("Using ENV WALLET_SECRET_BASE64/MNEMONIC_BASE64")
        kp  = keypair_from_b64(env_secret_b64.strip())
        pub = str(kp.pubkey())
        done(f"pubkey {pub}")
        if os.getenv("EXPECTED_PUBKEY") and os.getenv("EXPECTED_PUBKEY").strip() != pub:
            err("Derived pubkey != EXPECTED_PUBKEY")
            raise SystemExit(f"expected {os.getenv('EXPECTED_PUBKEY')} but got {pub}")
        return kp, pub, "ENV:BASE64"

    err("No signer provided")
    raise SystemExit("Provide signer via signer.txt, HARDCODE_SECRET_B64, CLI, or ENV.")

# ---------- IDL ----------
async def fetch_idl_onchain(rpc_url: str) -> Optional[Idl]:
    client = AsyncClient(rpc_url, commitment=Confirmed)
    provider = Provider(client, Wallet(Keypair()))
    try:
        idl = await Program.fetch_idl(PERPS_PROGRAM_ID, provider)
        await client.close(); return idl
    except Exception as e:
        d(f"IDL fetch failed: {e}")
        await client.close(); return None

def save_idl_to_path(idl: Idl, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(idl.to_json(), f, indent=2)

async def ensure_idl(rpc_url: str, path: Path, force_refresh: bool=False) -> Idl:
    say("Ensuring IDL")
    if force_refresh and path.exists():
        try: path.unlink(); info(f"Removed stale IDL at {path}")
        except Exception as e: warn(f"Could not remove IDL: {e}")
    if path.exists():
        info(f"Loading IDL from {path}")
        text = path.read_text(encoding="utf-8")
        try:    idl = Idl.from_json(text)
        except TypeError:
                idl = Idl.from_json(json.loads(text))
        done("IDL loaded from disk")
        return idl
    info("Fetching IDL from chain")
    idl = await fetch_idl_onchain(rpc_url)
    if idl is None:
        err("Failed to fetch IDL"); raise SystemExit(f"Place the IDL at {path}")
    save_idl_to_path(idl, path)
    done(f"IDL saved to {path}")
    return idl

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

# ---------- balances ----------
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
    eth,  eth_ata,  eth_exists  = await fetch_spl_ui_balance(client, owner, WETH_MINT)
    btc,  btc_ata,  btc_exists  = await fetch_spl_ui_balance(client, owner, WBTC_MINT)
    log("— Wallet Balances —")
    log(f"SOL : {sol:.9f} ({lamports} lamports)")
    log(f"USDC: {usdc:.6f} (ATA: {str(usdc_ata)}{' ✅' if usdc_exists else ' ❌ not found'})")
    log(f"ETH : {eth:.6f} (wETH mint {str(WETH_MINT)[:6]}…  ATA: {str(eth_ata)}{' ✅' if eth_exists else ' ❌ not found'})")
    log(f"BTC : {btc:.6f} (BTC mint  {str(WBTC_MINT)[:6]}… ATA: {str(btc_ata)}{' ✅' if btc_exists else ' ❌ not found'})")
    log("--------------------")
    done("balances OK")
    return sol, usdc, eth, btc

# ---------- helpers ----------
def to_snake_keys(d: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        s = []
        for ch in k:
            s.append("_" + ch.lower() if ch.isupper() else ch)
        key = "".join(s)
        if key.startswith("_"): key = key[1:]
        out[key] = v
    return out

def _camel_to_snake(name: str) -> str:
    out = []
    for ch in name:
        out.append("_" + ch.lower() if ch.isupper() else ch)
    s = "".join(out)
    return s[1:] if s.startswith("_") else s

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

# ---------- resolve RPC / methods ----------
def resolve_rpc_call(program: Program, ix_name: str) -> Tuple[Optional[Any], str, List[str]]:
    rpc_obj = program.rpc
    rpc_names: List[str] = []
    fn = None; chosen = ix_name
    if isinstance(rpc_obj, Mapping) or isinstance(rpc_obj, dict):
        rpc_names = list(rpc_obj.keys())
        info(f"Program.rpc mapping keys: {', '.join(rpc_names)}")
        key = _best_key(rpc_names, ix_name)
        if key: chosen = key; fn = rpc_obj[key]
    else:
        rpc_names = [n for n in dir(rpc_obj) if not n.startswith("_")]
        info(f"Program.rpc attributes: {', '.join(rpc_names)}")
        key = _best_key(rpc_names, ix_name)
        if key: chosen = key; fn = getattr(rpc_obj, key, None)
    return fn, chosen, rpc_names

def resolve_methods_builder(program: Program, ix_name: str) -> Tuple[Optional[Any], str, List[str]]:
    methods_obj = getattr(program, "methods", None)
    if methods_obj is None:
        return None, ix_name, []
    method_names: List[str] = []
    builder = None; chosen = ix_name
    if isinstance(methods_obj, Mapping) or isinstance(methods_obj, dict):
        method_names = list(methods_obj.keys())
        info(f"Program.methods mapping keys: {', '.join(method_names)}")
        key = _best_key(method_names, ix_name)
        if key: chosen = key; builder = methods_obj[key]
    else:
        method_names = [n for n in dir(methods_obj) if not n.startswith("_")]
        info(f"Program.methods attributes: {', '.join(method_names)}")
        key = _best_key(method_names, ix_name)
        if key and hasattr(methods_obj, key):
            chosen = key; builder = getattr(methods_obj, key)
    return builder, chosen, method_names

# ---------- call helpers ----------
async def call_with_param_styles(fn, ix_name: str, accounts: dict, params_lower: dict, params_caps: dict, program: Program):
    """
    Try both enum casings using ctx=Context(accounts=snake_case_map).
    """
    accounts_snake = to_snake_keys(accounts)
    ctx = Context(accounts=accounts_snake, signers=[])

    # simulate (lower) using method name
    try:
        say("Simulating (lower)")
        sim = await program.simulate(ix_name, {"params": params_lower}, ctx=ctx)
        if getattr(sim, "value", None) and getattr(sim.value, "logs", None):
            info("simulation logs (lower):")
            for x in sim.value.logs: print(x)
    except Exception as e:
        warn(f"simulate (lower) raised: {e}")

    # wrapped -> naked (lower)
    for label, pargs, pkwargs in (
        ("lower/wrapped", ({"params": params_lower},), {"ctx": ctx}),
        ("lower/naked",   (params_lower,),            {"ctx": ctx}),
    ):
        try:
            say(f"Submitting via Program.rpc ({label})")
            return await fn(*pargs, **pkwargs)
        except Exception as e:
            warn(f"Program.rpc {label} failed: {e}")

    # simulate (caps)
    try:
        say("Simulating (caps)")
        sim2 = await program.simulate(ix_name, {"params": params_caps}, ctx=ctx)
        if getattr(sim2, "value", None) and getattr(sim2.value, "logs", None):
            info("simulation logs (caps):")
            for x in sim2.value.logs: print(x)
    except Exception as e:
        warn(f"simulate (caps) raised: {e}")

    # wrapped -> naked (caps)
    for label, pargs, pkwargs in (
        ("caps/wrapped", ({"params": params_caps},), {"ctx": ctx}),
        ("caps/naked",   (params_caps,),            {"ctx": ctx}),
    ):
        try:
            say(f"Submitting via Program.rpc ({label})")
            return await fn(*pargs, **pkwargs)
        except Exception as e:
            warn(f"Program.rpc {label} failed: {e}")

    raise SystemExit("Could not invoke Program.rpc; tried ctx with snake_case accounts and both enum casings.")

async def call_via_methods(builder, ix_name: str, accounts: dict, params_lower: dict, params_caps: dict, program: Program):
    ix = next(i for i in program.idl.instructions if i.name == ix_name)
    nargs = len(ix.args)
    attempts: List[Tuple[str, List[Any]]] = []
    if nargs == 1:
        attempts += [
            ("lower/wrapped", [ {"params": params_lower} ]),
            ("lower/naked",   [ params_lower ]),
            ("caps/wrapped",  [ {"params": params_caps} ]),
            ("caps/naked",    [ params_caps ]),
        ]
    else:
        attempts += [("lower/naked", [params_lower]), ("caps/naked", [params_caps])]

    for label, arglist in attempts:
        try:
            say(f"Submitting via Program.methods ({label})")
            mb = builder(*arglist).accounts(to_snake_keys(accounts))
            sig = await mb.rpc()
            return sig
        except Exception as e:
            warn(f"Program.methods {label} failed: {e}")
    raise SystemExit("Could not invoke Program.methods; see above errors.")

async def call_via_instruction(program: Program, ix_name: str, accounts: dict, params: dict, kp: Keypair, client: AsyncClient) -> str:
    instr_ns = getattr(program, "instruction", None)
    if not instr_ns:
        raise SystemExit("Program.instruction not available.")
    names: List[str] = []
    fn = None
    if isinstance(instr_ns, Mapping) or isinstance(instr_ns, dict):
        names = list(instr_ns.keys()); info(f"Program.instruction mapping keys: {', '.join(names)}")
        key = _best_key(names, ix_name)
        if key: fn = instr_ns[key]
    else:
        names = [n for n in dir(instr_ns) if not n.startswith("_")]
        info(f"Program.instruction attributes: {', '.join(names)}")
        key = _best_key(names, ix_name)
        if key: fn = getattr(instr_ns, key, None)
    if not fn:
        raise SystemExit("Could not resolve Program.instruction builder.")

    accounts_snake = to_snake_keys(accounts)
    combos = [
        ("wrapped/ctx",  ({"params": params},), {"ctx": Context(accounts=accounts_snake, signers=[])}),
        ("wrapped/acc",  ({"params": params}, accounts_snake), {}),
        ("wrapped/kwacc",({"params": params},), {"accounts": accounts_snake}),
        ("naked/ctx",    (params,), {"ctx": Context(accounts=accounts_snake, signers=[])}),
        ("naked/acc",    (params, accounts_snake), {}),
        ("naked/kwacc",  (params,), {"accounts": accounts_snake}),
    ]
    for label, pargs, pkwargs in combos:
        try:
            say(f"Building Instruction via Program.instruction ({label})")
            ix = await fn(*pargs, **pkwargs)
            recent = await client.get_latest_blockhash()
            tx = Transaction(fee_payer=kp.pubkey(), recent_blockhash=recent.value.blockhash)
            tx.add(ix)
            sig = await client.send_transaction(tx, kp, opts=TxOpts(skip_preflight=False, preflight_commitment=Processed))
            await client.confirm_transaction(sig.value, commitment=Confirmed)
            return sig.value
        except Exception as e:
            warn(f"instruction {label} failed: {e}")
    raise SystemExit("Program.instruction fallback failed with all arg styles.")

# ---------- simple ATA ensure ----------
def build_create_ata_ix(payer: Pubkey, owner: Pubkey, mint: Pubkey, ata: Pubkey) -> Instruction:
    return Instruction(
        program_id=ASSOCIATED_TOKEN_PROGRAM,
        accounts=(
            AccountMeta(payer, is_signer=True,  is_writable=True),
            AccountMeta(ata,   is_signer=False, is_writable=True),
            AccountMeta(owner, is_signer=False, is_writable=False),
            AccountMeta(mint,  is_signer=False, is_writable=False),
            AccountMeta(SYSTEM_PROGRAM,         is_signer=False, is_writable=False),
            AccountMeta(TOKEN_PROGRAM,          is_signer=False, is_writable=False),
            AccountMeta(RENT_SYSVAR_DEPRECATED, is_signer=False, is_writable=False),
        ),
        data=b"",
    )

async def ensure_ata(client: AsyncClient, kp: Keypair, owner: Pubkey, mint: Pubkey) -> Pubkey:
    ata = derive_ata(owner, mint)
    info_ = await client.get_account_info(ata)
    if info_.value is not None:
        d(f"ATA exists for mint={mint} at {ata}")
        return ata
    say("Creating missing ATA")
    info(f"mint={str(mint)}"); info(f"ata ={str(ata)}")
    ix     = build_create_ata_ix(owner, owner, mint, ata)
    recent = await client.get_latest_blockhash()
    tx     = Transaction(fee_payer=owner, recent_blockhash=recent.value.blockhash)
    tx.add(ix)
    sig = await client.send_transaction(tx, kp, opts=TxOpts(skip_preflight=False, preflight_commitment=Processed))
    await client.confirm_transaction(sig.value, commitment=Confirmed)
    done(f"ATA created (tx: {sig.value})")
    return ata

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
        await client.close()
        err("Insufficient SOL for fees/rent"); raise SystemExit("Not enough SOL — top up and retry.")
    done("fee/rent OK")

    # 3) preflight: USDC
    say("Preflight: USDC collateral check")
    need_usdc = collateral_atoms / (10 ** USDC_DECIMALS)
    info(f"have {usdc:.6f} USDC   need {need_usdc:.6f} USDC")
    if need_usdc > 0 and usdc + 1e-9 < need_usdc:
        await client.close()
        err("Insufficient USDC collateral"); raise SystemExit("Not enough USDC — deposit or reduce collateral amount.")
    done("collateral OK")

    # 4) ensure USDC ATA
    usdc_ata = await ensure_ata(client, kp, owner, USDC_MINT)

    # 5) PDAs & ix name
    say("Deriving PDAs & choosing instruction")
    position         = derive_position_pda(owner, POOL, CUSTODY_SOL, CUSTODY_USDC)
    counter          = int(time.time())
    position_request = derive_position_request_pda(position, counter)
    names = [ix.name for ix in idl.instructions]
    d(f"IDL instructions: {names}")
    target_ix = None
    for cand in ("createIncreasePositionMarketRequest", "createPositionRequest"):
        if cand in names: target_ix = cand; break
    if not target_ix:
        for ix in idl.instructions:
            nl = ix.name.lower()
            if "position" in nl and "request" in nl: target_ix = ix.name; break
    if not target_ix:
        await client.close(); raise SystemExit(f"No suitable instruction found. Available: {names}")
    ix_name = target_ix
    info(f"instruction: {ix_name}")
    d(f"owner           : {owner}")
    d(f"pool            : {POOL}")
    d(f"custody (SOL)   : {CUSTODY_SOL}")
    d(f"custody (USDC)  : {CUSTODY_USDC}")
    d(f"position PDA    : {position}")
    d(f"positionRequest : {position_request}")
    d(f"usdc ATA        : {usdc_ata}")
    done("PDAs ready")

    # 6) params
    params_lower = {"side":{"long":{}}, "requestType":{"market":{}}, "requestChange":{"increase":{}}, "sizeUsdDelta":size_usd_6dp, "collateralDelta":collateral_atoms, "priceSlippage":max_price_usd_6dp, "jupiterMinimumOut":0, "triggerPrice":0, "triggerAboveThreshold":False, "entirePosition":False}
    params_caps  = {"side":{"Long":{}}, "requestType":{"Market":{}}, "requestChange":{"Increase":{}}, "sizeUsdDelta":size_usd_6dp, "collateralDelta":collateral_atoms, "priceSlippage":max_price_usd_6dp, "jupiterMinimumOut":0, "triggerPrice":0, "triggerAboveThreshold":False, "entirePosition":False}

    # 7) accounts map (camel & snake)
    def build_accounts_dict_from_idl(idl_obj: Idl, ix_nm: str, base: Dict[str, Pubkey]) -> Dict[str, Pubkey]:
        ix = next(i for i in idl_obj.instructions if i.name == ix_nm)
        needed = [acc.name for acc in ix.accounts]
        accounts: Dict[str, Pubkey] = {}
        owner_ = base["owner"]; position_ = base["position"]
        commons = {"fundingAccount": derive_ata(owner_, USDC_MINT), "perpetuals": derive_perpetuals_pda(),
                   "positionRequestAta": derive_ata(owner_, position_), "inputMint": USDC_MINT, "referral": owner_,
                   "tokenProgram": TOKEN_PROGRAM, "associatedTokenProgram": ASSOCIATED_TOKEN_PROGRAM, "systemProgram": SYSTEM_PROGRAM,
                   "eventAuthority": derive_event_authority(), "program": PERPS_PROGRAM_ID, "rent": RENT_SYSVAR_DEPRECATED}
        for k, v in base.items(): accounts[k] = v
        for name in needed:
            if name not in accounts and name in commons: accounts[name] = commons[name]
            elif name not in accounts:
                alias={"token_program":"tokenProgram","system_program":"systemProgram","associated_token_program":"associatedTokenProgram","payer":"owner","rentSysvar":"rent"}.get(name)
                if alias and alias in commons: accounts[name]=commons[alias]
        missing=[n for n in needed if n not in accounts]
        if missing: raise SystemExit(f"Missing accounts for {ix_nm}: {missing}\nNeeded={needed}\nHave={list(accounts.keys())}")
        return accounts

    base_accounts = {"owner":owner, "pool":POOL, "custody":CUSTODY_SOL, "collateralCustody":CUSTODY_USDC, "position":position, "positionRequest":position_request}
    accounts = build_accounts_dict_from_idl(idl, ix_name, base_accounts)
    accounts_snake = to_snake_keys(accounts)

    say("Dumping params & accounts")
    info("params (lower):");        print(json.dumps(params_lower, indent=2))
    info("accounts (camel):");      print(json.dumps({k: str(v) for k,v in accounts.items()}, indent=2))
    info("accounts (snake):");      print(json.dumps({k: str(v) for k,v in accounts_snake.items()}, indent=2))
    done("dumped")

    # 8) resolve rpc call
    say("Resolving RPC method in anchorpy bindings")
    rpc_fn, chosen_rpc, avail_rpc = resolve_rpc_call(program, ix_name)
    if rpc_fn:
        info(f"RPC method chosen: {chosen_rpc}")
        if dry_run:
            await client.close(); warn("dry-run enabled — not sending tx"); return "dry-run"
        sig = await call_with_param_styles(rpc_fn, chosen_rpc, accounts, params_lower, params_caps, program)
        await client.close()
        done(f"submitted → {sig}")
        info(f"PositionRequest PDA: {str(position_request)}"); info(f"Position PDA       : {str(position)}")
        log("ℹ️ Keepers will fulfill the request if it passes all checks.")
        return sig

    warn("RPC method not found in Program.rpc, falling back to Program.methods")
    info(f"IDL ix name     : {ix_name}")
    info(f"RPC snake guess : {_camel_to_snake(ix_name)}")
    info(f"Available RPCs  : {', '.join(avail_rpc) if avail_rpc else '(none)'}")

    methods_builder, chosen_method, avail_methods = resolve_methods_builder(program, ix_name)
    if methods_builder:
        info(f"Methods builder chosen: {chosen_method}")
        if dry_run:
            await client.close(); warn("dry-run enabled — not sending tx"); return "dry-run"
        try:
            say("Simulating (lower)")
            sim = await program.simulate(ix_name, {"params": params_lower}, ctx=Context(accounts=accounts_snake, signers=[]))
            if getattr(sim, "value", None) and getattr(sim.value, "logs", None):
                info("simulation logs (lower):"); [print(x) for x in sim.value.logs]
        except Exception as e: warn(f"simulate (lower) raised: {e}")
        sig = await call_via_methods(methods_builder, ix_name, accounts, params_lower, params_caps, program)
        await client.close()
        done(f"submitted → {sig}")
        info(f"PositionRequest PDA: {str(position_request)}"); info(f"Position PDA       : {str(position)}")
        return sig

    warn("No suitable method in Program.methods; attempting Program.instruction fallback")
    info(f"Available methods: {', '.join(avail_methods) if avail_methods else '(none)'}")
    if dry_run:
        await client.close(); warn("dry-run enabled — not sending tx"); return "dry-run"

    # instruction fallback
    try:
        sig = await call_via_instruction(program, ix_name, accounts, params_lower, kp, client)
        await client.close()
        done(f"submitted → {sig}")
        info(f"PositionRequest PDA: {str(position_request)}"); info(f"Position PDA       : {str(position)}")
        return sig
    except Exception as e1:
        warn(f"instruction/lower failed: {e1}")
    try:
        sig = await call_via_instruction(program, ix_name, accounts, params_caps, kp, client)
        await client.close()
        done(f"submitted → {sig}")
        info(f"PositionRequest PDA: {str(position_request)}"); info(f"Position PDA       : {str(position)}")
        return sig
    except Exception as e2:
        await client.close()
        err("All invocation strategies failed.")
        raise SystemExit(str(e2))

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

    kp, pub, src = resolve_signer(args, env_secret, env_mnemonic, env_mpass, env_dpath, signer_file_env)

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
