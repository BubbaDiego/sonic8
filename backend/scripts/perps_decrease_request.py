#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import struct
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.hash import Hash
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.message import to_bytes_versioned
from solders.instruction import Instruction
from solders.compute_budget import set_compute_unit_price, set_compute_unit_limit

# ---------------- CONFIG (EDIT) ----------------
HELIUS_API_KEY = "a8809bee-20ba-48e9-b841-0bd2bafd60b9"
RPC_URL        = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Correct mainnet Perps program id (you verified this)
PROGRAM_ID     = Pubkey.from_string("PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu")

# Your wallet (the one that owns the position)
OWNER          = Pubkey.from_string("V8iveiirFvX7m7psPHWBJW85xPk1ZB6U4Ep9GUV2THW")

# One of your position pubkeys to decrease/close
POSITION_PUBKEY = Pubkey.from_string("2ZwGG1dKAHCQErH3cNychmQm6tBWSLdhKQrSc2XKP6hZ")  # change to any of your 4

# Where your canonical IDL JSON is saved
IDL_PATH       = r"C:\sonic5\backend\services\perps\idl\jupiter_perpetuals.json"

# Decrease params (u64 in USD units of the program; often 1e6 implies $1 = 1_000_000)
SIZE_USD_DELTA      = 0          # set >0 to reduce notional (e.g., 50_000_000 == $50)
COLLATERAL_USD_DELTA= 0          # set >0 to withdraw collateral USD
PRICE_SLIPPAGE      = 0          # program-specific units; if unsure, keep 0
ENTIRE_POSITION     = True       # True to request full close
DESIRED_MINT        = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC

# Priority fees / compute
PRIORITY_MICROLAMPORTS = 100_000  # ~0.0001 SOL per CU price; adjust
CU_LIMIT               = 900_000

# Signer: put your id.json OR base58 secret here
SIGNER_PATH_OR_BASE58 = r"C:\sonic5\signer.txt"  # or paste base58 string
# -----------------------------------------------

SPL_TOKEN_PROGRAM_ID   = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROG  = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
SYSTEM_PROGRAM_ID      = Pubkey.from_string("11111111111111111111111111111111")


# ---------------- small RPC helpers ----------------
def rpc(method: str, params: Any) -> Any:
    r = requests.post(RPC_URL, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result")

def get_account_json(pubkey: Pubkey) -> Dict[str, Any]:
    res = rpc("getAccountInfo", [str(pubkey), {"encoding":"jsonParsed","commitment":"confirmed"}])
    v = res.get("value")
    if not v:
        raise RuntimeError(f"no account info for {pubkey}")
    return v

def get_account_raw(pubkey: Pubkey) -> bytes:
    res = rpc("getAccountInfo", [str(pubkey), {"encoding":"base64","commitment":"confirmed"}])
    v = res.get("value")
    if not v:
        return b""
    data = v.get("data", [])
    if isinstance(data, list) and data and isinstance(data[0], str):
        return base64.b64decode(data[0])
    if isinstance(data, dict) and "encoded" in data:
        return base64.b64decode(data["encoded"])
    return b""

def get_multiple_accounts_raw(pubs: list[Pubkey]) -> list[Optional[bytes]]:
    res = rpc("getMultipleAccounts", [[str(p) for p in pubs], {"encoding":"base64","commitment":"confirmed"}])
    vals = res.get("value", [])
    out=[]
    for v in vals:
        if not isinstance(v, dict):
            out.append(None); continue
        data = v.get("data", [])
        if isinstance(data, list) and data and isinstance(data[0], str):
            out.append(base64.b64decode(data[0])); continue
        if isinstance(data, dict) and "encoded" in data:
            out.append(base64.b64decode(data["encoded"])); continue
        out.append(None)
    return out

def recent_blockhash() -> Hash:
    res = rpc("getLatestBlockhash", [{"commitment":"finalized"}])
    return Hash.from_string(res["value"]["blockhash"])


# ---------------- key loading ----------------
# ------- helpers for base58 (no external dep) -------
_B58_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_IDX  = {ch: i for i, ch in enumerate(_B58_ALPH)}
def _b58decode(s: str) -> bytes:
    n = 0
    for ch in s.strip():
        if ch not in _B58_IDX:
            raise ValueError(f"Invalid character '{ch}' in base58 string")
        n = n * 58 + _B58_IDX[ch]
    full = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b"\x00"
    # preserve leading '1' (zero bytes)
    leading = 0
    for ch in s:
        if ch == "1":
            leading += 1
        else:
            break
    return b"\x00" * leading + full.lstrip(b"\x00")


def load_signer(path_or_base58: str) -> Keypair:
    """
    Accepted inputs:
      - path to id.json (array of 64 ints) or {"secretKey":[...]}
      - path to key=value text: mnemonic=/phrase= [passphrase=], base58=/secret=
      - raw base58 secret string (32- or 64-byte)
    """
    s = path_or_base58.strip()

    # 1) File on disk?
    if os.path.exists(s):
        txt = open(s, "r", encoding="utf-8").read().strip()

        # 1a) Try JSON (id.json or object)
        try:
            obj = json.loads(txt)
            if isinstance(obj, list):
                # id.json: list of 64 ints
                return Keypair.from_bytes(bytes(obj))
            if isinstance(obj, dict):
                if "secretKey" in obj and isinstance(obj["secretKey"], list):
                    return Keypair.from_bytes(bytes(obj["secretKey"]))
                # JSON object with mnemonic/phrase
                mn = obj.get("mnemonic") or obj.get("phrase")
                if isinstance(mn, str):
                    pp = obj.get("passphrase") or ""
                    return _derive_from_mnemonic(mn, pp)
        except Exception:
            pass  # not JSON → fall through

        # 1b) key=value text
        kv = {}
        for line in txt.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # accept ":" or "=" as delimiter
            if ":" in line and "=" not in line:
                k, v = line.split(":", 1)
            elif "=" in line:
                k, v = line.split("=", 1)
            else:
                # no delimiter → maybe it's base58 directly
                k, v = "base58", line
            kv[k.strip().lower()] = v.strip().strip('"').strip("'")

        # prefer mnemonic/phrase
        mn = kv.get("mnemonic") or kv.get("phrase")
        if mn:
            pp = kv.get("passphrase", "")
            return _derive_from_mnemonic(mn, pp)

        # base58/secret in the file
        sec = kv.get("base58") or kv.get("secret") or kv.get("private")
        if sec:
            return _kp_from_base58(sec)

        # as a last resort, if the whole file looks like base58, try it
        try:
            return _kp_from_base58(txt)
        except Exception as e:
            raise RuntimeError(f"Unsupported signer format in '{s}': {e}")

    # 2) Not a file → assume raw base58 key
    return _kp_from_base58(s)


def _kp_from_base58(b58: str) -> Keypair:
    raw = _b58decode(b58)
    if len(raw) == 64:
        # full 64-byte secret key
        return Keypair.from_bytes(raw)
    if len(raw) == 32:
        # seed → try Keypair.from_seed (preferred)
        try:
            return Keypair.from_seed(raw)
        except Exception:
            # fallback via pynacl if available
            try:
                import nacl.signing as ns
                sk = ns.SigningKey(raw)
                sec64 = sk.encode() + sk.verify_key.encode()
                return Keypair.from_bytes(sec64)
            except Exception as ee:
                raise RuntimeError(f"32-byte seed given, but cannot construct keypair: {ee}")
    raise ValueError(f"base58 decoded length {len(raw)} not 32/64 bytes")


def _derive_from_mnemonic(mnemonic: str, passphrase: str = "") -> Keypair:
    """
    Derive Solana keypair from BIP-39 mnemonic using path m/44'/501'/0'/0'.
    Works across bip_utils versions (RawUncompressed/RawCompressed/Raw).
    Requires: bip_utils (pip install bip_utils) and PyNaCl (fallback).
    """
    try:
        from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes

        # 1) BIP39 seed
        seed = Bip39SeedGenerator(mnemonic).Generate(passphrase)

        # 2) Standard Solana derivation: m/44'/501'/0'/0'
        node = (Bip44.FromSeed(seed, Bip44Coins.SOLANA)
                .Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0))

        # 3) Get private key bytes (handle API differences)
        pk_obj = node.PrivateKey()
        priv_bytes = None
        for attr in ("RawUncompressed", "RawCompressed", "Raw"):
            if hasattr(pk_obj, attr):
                priv_bytes = getattr(pk_obj, attr)().ToBytes()
                break
        if priv_bytes is None:
            raise RuntimeError("Unsupported bip_utils version: no Raw*/ToBytes on private key")

        # Some versions give 32 bytes (seed) — perfect.
        # Others may return 64 byte material; first 32 are the seed for ed25519.
        if len(priv_bytes) >= 32:
            seed32 = priv_bytes[:32]
        else:
            raise RuntimeError(f"Unexpected private key length: {len(priv_bytes)}")

        # 4) Build solders keypair from the 32-byte seed
        try:
            return Keypair.from_seed(seed32)
        except Exception:
            # Fallback via PyNaCl if some environments need it
            import nacl.signing as ns
            sk = ns.SigningKey(seed32)
            sec64 = sk.encode() + sk.verify_key.encode()
            return Keypair.from_bytes(sec64)

    except ImportError:
        raise RuntimeError(
            "Mnemonic present but 'bip_utils' (and optionally 'pynacl') not installed. "
            "Install with: pip install bip_utils pynacl"
        )

# ---------------- IDL loader + decode aids ----------------
def disc_for_account(name: str) -> bytes:
    return hashlib.sha256(f"account:{name}".encode("utf-8")).digest()[:8]

def parse_position_accounts_and_fields() -> dict:
    """Read Position account, extract pool/custody/collateralCustody, also Perpetuals PDA."""
    raw = get_account_raw(POSITION_PUBKEY)
    if len(raw) < 8:
        raise RuntimeError("position account too small")
    # Verify discriminator matches "Position"
    want = disc_for_account("Position")
    if raw[:8] != want:
        # some builds rename; continue anyway
        pass
    # crude decode: owner(32),pool(32),custody(32),collateralCustody(32) follow after disc; consult your IDL fields order
    # disc(8) + owner(32) + pool(32) + custody(32) + collateralCustody(32)
    if len(raw) < 8 + 32*4:
        raise RuntimeError("position account not large enough to parse keys")
    off = 8
    owner = Pubkey.from_bytes(raw[off:off+32]); off += 32
    pool  = Pubkey.from_bytes(raw[off:off+32]); off += 32
    custody = Pubkey.from_bytes(raw[off:off+32]); off += 32
    collateral_custody = Pubkey.from_bytes(raw[off:off+32]); off += 32
    return {
        "owner_from_position": owner,
        "pool": pool,
        "custody": custody,
        "collateral_custody": collateral_custody
    }

def load_idl() -> dict:
    with open(IDL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------- PDA derivations ----------------
def find_perpetuals_account() -> Pubkey:
    """Find the unique Perpetuals root account by scanning first page (disc match)."""
    params={"encoding":"base64","dataSlice":{"offset":0,"length":8},"limit":1000}
    res = rpc("getProgramAccountsV2", [str(PROGRAM_ID), params]) or {}
    accs = res.get("accounts") if isinstance(res, dict) else []
    target = disc_for_account("Perpetuals")
    for it in accs:
        if not isinstance(it, dict): continue
        pk = it.get("pubkey")
        data = (it.get("account") or {}).get("data")
        raw8=None
        if isinstance(data, list) and data and isinstance(data[0], str):
            raw8 = base64.b64decode(data[0])
        elif isinstance(data, dict) and "encoded" in data:
            raw8 = base64.b64decode(data["encoded"])
        if isinstance(raw8, (bytes, bytearray)) and len(raw8)>=8 and raw8[:8]==target:
            return Pubkey.from_string(pk)
    raise RuntimeError("Perpetuals account not found")

def find_custody_accounts(pubkey_list: list[Pubkey]) -> dict:
    """Fetch raw for custody and collateralCustody; read their oracle mints and tokenAccount etc."""
    raws = get_multiple_accounts_raw(pubkey_list)
    out={}
    for pk, raw in zip(pubkey_list, raws):
        if not isinstance(raw, (bytes,bytearray)) or len(raw)<8:
            continue
        # verify disc match "Custody"
        want = disc_for_account("Custody")
        if raw[:8] != want:
            # continue but trust IDL field offsets approx.; we won't fully decode all fields
            pass
        # Custody struct layout per your IDL:
        # disc(8) + pool(32) + mint(32) + tokenAccount(32) + decimals(1) + isStable(1) + ...
        off = 8 + 32  # skip pool
        mint = Pubkey.from_bytes(raw[off:off+32]); off += 32
        token_account = Pubkey.from_bytes(raw[off:off+32]); off += 32
        # We won't parse all; we need dovesOracle and dovesAgOracle later; leave None if unknown
        out[str(pk)] = {"mint": mint, "token_account": token_account}
    return out

def pda_event_authority(program_id: Pubkey) -> Pubkey:
    seed = [b"__event_authority"]
    return Pubkey.find_program_address(seed, program_id)[0]

def ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    seed = [bytes(owner), bytes(SPL_TOKEN_PROGRAM_ID), bytes(mint)]
    return Pubkey.find_program_address(seed, ASSOCIATED_TOKEN_PROG)[0]

def derive_position_request_pda(owner: Pubkey, position: Pubkey, counter: int) -> Pubkey:
    """
    PDA layout is not published in IDL; this derivation is a best-guess that matches common patterns:
    seeds = [b"position-request", owner, position, counter_le_u64]
    """
    ctr_le = struct.pack("<Q", counter)
    seeds = [b"position-request", bytes(owner), bytes(position), ctr_le]
    return Pubkey.find_program_address(seeds, PROGRAM_ID)[0]


# ---------------- tx builder ----------------
def make_accounts_and_ix(idl: dict, signer: Keypair) -> Instruction:
    # 1) parse Position → pool, custody, collateralCustody
    pos = parse_position_accounts_and_fields()
    pool = pos["pool"]; custody = pos["custody"]; coll_custody = pos["collateral_custody"]
    if OWNER != pos["owner_from_position"]:
        print("WARN: position owner in account != configured OWNER; continuing anyway.")

    # 2) resolve Perpetuals (unique)
    perpetuals = find_perpetuals_account()

    # 3) desired mint & receiving ATA (owner’s USDC by default)
    desired_mint = Pubkey.from_string(DESIRED_MINT)
    receiving_ata = ata(OWNER, desired_mint)

    # 4) derive a counter; simplest is epoch seconds — contracts that embed counter will accept any
    counter = int(time.time())  # if program expects monotonic counter; adjust if needed
    position_request = derive_position_request_pda(OWNER, POSITION_PUBKEY, counter)
    position_request_ata = ata(position_request, desired_mint)

    # 5) custodies → token accounts (escrow) and oracles (best-effort: we use token_account only here)
    cust_info = find_custody_accounts([custody, coll_custody])
    custody_token_account = cust_info.get(str(coll_custody), {}).get("token_account")
    if not custody_token_account:
        raise RuntimeError("could not resolve collateralCustodyTokenAccount")

    # 6) event authority & program id account
    event_authority = pda_event_authority(PROGRAM_ID)
    program_id_acc = PROGRAM_ID

    # 7) build params struct for CreateDecreasePositionRequest2Params
    # fields: collateralUsdDelta (u64), sizeUsdDelta (u64), requestType(enum), priceSlippage(opt u64),
    #         jupiterMinimumOut(opt u64), triggerPrice(opt u64), triggerAboveThreshold(opt bool),
    #         entirePosition(opt bool), counter(u64)
    # We use requestType = Market (0) by convention in this build. Adjust if your IDL enum indices differ.
    params = {
        "collateralUsdDelta": int(COLLATERAL_USD_DELTA),
        "sizeUsdDelta": int(SIZE_USD_DELTA),
        "requestType": {"market": {}} ,  # AnchorPy lowercases enum variant; if fails, swap to 0
        "priceSlippage": None if PRICE_SLIPPAGE == 0 else int(PRICE_SLIPPAGE),
        "jupiterMinimumOut": None,
        "triggerPrice": None,
        "triggerAboveThreshold": None,
        "entirePosition": ENTIRE_POSITION,
        "counter": int(counter)
    }

    # 8) assemble account metas in the exact order the IDL printed (isMut/isSigner must match)
    keys = [
        (OWNER,            True,  True),   # owner
        (receiving_ata,    True,  False),  # receivingAccount
        (perpetuals,       False, False),  # perpetuals
        (pool,             False, False),  # pool
        (POSITION_PUBKEY,  False, False),  # position
        (position_request, True,  False),  # positionRequest (PDA, created)
        (position_request_ata, True, False), # positionRequestAta (escrow ATA for desiredMint)
        (custody,          False, False),  # custody
        (Pubkey.default(), False, False),  # custodyDovesPriceAccount (unknown here; pass default if program allows None)
        (Pubkey.default(), False, False),  # custodyPythnetPriceAccount
        (coll_custody,     False, False),  # collateralCustody
        (desired_mint,     False, False),  # desiredMint
        (Pubkey.default(), False, False),  # referral (optional)
        (SPL_TOKEN_PROGRAM_ID, False, False),   # tokenProgram
        (ASSOCIATED_TOKEN_PROG, False, False),  # associatedTokenProgram
        (SYSTEM_PROGRAM_ID, False, False),      # systemProgram
        (event_authority, False, False),        # eventAuthority
        (program_id_acc,  False, False)         # program
    ]

    # 9) use Anchor IDL to serialize instruction data
    from anchorpy import Idl, Program, Provider, Wallet
    from solana.rpc.async_api import AsyncClient  # just for provider; we won't use async send
    # fake async provider just to use coder; we will craft Instruction manually
    idl_obj = Idl.from_json(idl)
    # encode instruction data via coder
    method_name = "createDecreasePositionRequest2"
    ix_def = next(ix for ix in idl_obj.instructions if ix.name == method_name)
    data = idl_obj.coder.build(ix_def, [params])

    # Convert to solders.Instruction
    metas = []
    from solders.account_meta import AccountMeta
    for pub, is_mut, is_signer in keys:
        metas.append(AccountMeta(pub, is_signer, is_mut))
    return Instruction(PROGRAM_ID, data, metas)


# ---------------- main ----------------
def main():
    # sanity
    if not os.path.exists(IDL_PATH):
        print(f"IDL JSON not found: {IDL_PATH}")
        sys.exit(1)

    # Load IDL
    try:
        idl = json.load(open(IDL_PATH, "r", encoding="utf-8"))
    except Exception as e:
        print("Failed to load IDL:", e); sys.exit(1)

    # Signer
    try:
        kp = load_signer(SIGNER_PATH_OR_BASE58)
    except Exception as e:
        print("Failed to load signer:", e); sys.exit(1)
    if kp.pubkey() != OWNER:
        print(f"WARN: signer pubkey != OWNER\n  signer={kp.pubkey()}\n  owner ={OWNER}")

    # Build instruction
    try:
        ix = make_accounts_and_ix(idl, kp)
    except Exception as e:
        print("Build failed:", e); sys.exit(1)

    # Transaction: add compute budget
    cu_price_ix = set_compute_unit_price(PRIORITY_MICROLAMPORTS)
    cu_limit_ix = set_compute_unit_limit(CU_LIMIT)

    # recent blockhash
    bh = recent_blockhash()
    msg = MessageV0.try_compile(
        payer=kp.pubkey(),
        instructions=[cu_price_ix, cu_limit_ix, ix],
        address_lookup_tables=[]
    )
    tx = VersionedTransaction(msg, [kp])

    # send
    try:
        raw = bytes(tx)
        res = rpc("sendTransaction", [base64.b64encode(raw).decode(), {"skipPreflight": False, "maxRetries": 3}])
        sig = res
        print("\nSent tx:", sig)
        print("Explorer:", f"https://solscan.io/tx/{sig}")
    except Exception as e:
        print("Send failed:", e)
        # try simulate for a clear error
        try:
            sim = rpc("simulateTransaction", [base64.b64encode(bytes(tx)).decode(), {"sigVerify": False}])
            print("Simulation result:", json.dumps(sim, indent=2))
        except Exception as ee:
            print("Simulate failed:", ee)


if __name__ == "__main__":
    main()
