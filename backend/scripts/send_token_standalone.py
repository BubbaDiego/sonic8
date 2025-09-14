#!/usr/bin/env python3
from __future__ import annotations
import base64, json, os, re, sys, requests

from typing import Any, Dict, List
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.hash import Hash
from solders.instruction import Instruction, AccountMeta
from solders.message import MessageV0, to_bytes_versioned
from solders.transaction import VersionedTransaction
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price

# ========================== CONFIG (EDIT) ==========================
HELIUS_API_KEY = "a8809bee-20ba-48e9-b841-0bd2bafd60b9"
RPC_URL        = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

SIGNER_FILE    = r"C:\sonic5\backend\signer.txt"  # id.json OR key=value with mnemonic/base58 OR raw base58

TOKEN          = "USDC"            # 'SOL', 'USDC', or a mint address
AMOUNT_UI      = 1.0               # human units (1 USDC, 0.005 SOL, …)
RECIPIENT      = "89YeqPcCey8h9Vzg9nCdzw1gCixA2nLg9jKgCtw2b9CZ"  # base58 OR solana:<pk>?… OR explorer URL

CU_LIMIT       = 800_000
CU_PRICE       = 100_000           # microlamports per CU (0.0001 SOL / 1e6 CU)
# ================================================================

SYSTEM_PROGRAM        = Pubkey.from_string("11111111111111111111111111111111")
SPL_TOKEN_PROGRAM     = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROG = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
RENT_SYSVAR           = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

SOL_MINT  = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# ----------------------- base58 helpers -----------------------
BASE58_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_SET  = set(BASE58_ALPH)
BASE58_RE   = re.compile(r"^[1-9A-HJ-NP-Za-km-z]+$")
BASE58_FIND = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,}")

def extract_pubkey(s: str) -> str:
    if not s: return ""
    s = str(s).strip()
    low = s.lower()
    if low.startswith("solana:"):
        return s.split(":", 1)[1].split("?", 1)[0]
    m = re.search(r"address/([1-9A-HJ-NP-Za-km-z]+)", s)
    if m: return m.group(1)
    s0 = re.split(r"[?#\s]", s)[0]
    if BASE58_RE.fullmatch(s0 or ""): return s0
    hits = BASE58_FIND.findall(s)
    if hits:
        hits.sort(key=len, reverse=True)
        return hits[0]
    return s0

def fail_if_bad_base58(label: str, pk: str) -> str:
    if not pk: die(f"Missing {label}")
    for i, ch in enumerate(pk):
        if ch not in BASE58_SET:
            die(f"Invalid {label}: invalid base58 char '{ch}' at index {i} in '{pk}'")
    return pk

def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(2)

# ----------------------- RPC helpers -----------------------
def rpc(method: str, params: Any) -> Any:
    r = requests.post(RPC_URL, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=25)
    r.raise_for_status()
    j = r.json()
    if j.get("error"): die(str(j["error"]))
    return j["result"]

def recent_blockhash() -> Hash:
    return Hash.from_string(rpc("getLatestBlockhash", [{"commitment":"finalized"}])["value"]["blockhash"])

def get_balance(pub: Pubkey) -> int:
    return int(rpc("getBalance", [str(pub)])["value"])

def get_min_rent_exempt(size: int) -> int:
    return int(rpc("getMinimumBalanceForRentExemption", [size]))

# ----------------------- signer loading -----------------------
def _b58decode(s: str) -> bytes:
    idx = {ch:i for i,ch in enumerate(BASE58_ALPH)}
    n = 0
    for ch in s.strip():
        if ch not in idx: raise ValueError(f"invalid base58 char: {ch}")
        n = n*58 + idx[ch]
    full = n.to_bytes((n.bit_length()+7)//8, "big") if n else b"\x00"
    lead = sum(1 for ch in s if ch=="1")
    return b"\x00"*lead + full.lstrip(b"\x00")

def parse_signer_txt(path: str) -> Dict[str, str]:
    txt = open(path, "r", encoding="utf-8").read()
    kv = {}
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        if "=" in line and ":" not in line: k,v = line.split("=",1)
        elif ":" in line and "=" not in line: k,v = line.split(":",1)
        else: kv["base58"] = line; continue
        kv[k.strip().lower()] = v.strip().strip('"').strip("'")
    return kv

def keypair_from_base58(sec_b58: str) -> Keypair:
    raw = _b58decode(sec_b58)
    if len(raw)==64: return Keypair.from_bytes(raw)
    if len(raw)==32:
        try: return Keypair.from_seed(raw)
        except Exception:
            import nacl.signing as ns
            sk = ns.SigningKey(raw)
            sec64 = sk.encode() + sk.verify_key.encode()
            return Keypair.from_bytes(sec64)
    die(f"base58 secret length {len(raw)} not 32/64")

def derive_from_mnemonic(mnemonic: str, passphrase: str = "") -> Keypair:
    try:
        from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
    except ImportError:
        die("Mnemonic present but 'bip_utils' not installed. Install: pip install bip_utils pynacl")
    seed = Bip39SeedGenerator(mnemonic).Generate(passphrase)
    node = (Bip44.FromSeed(seed, Bip44Coins.SOLANA)
            .Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0))
    pkobj = node.PrivateKey()
    priv = None
    for attr in ("RawUncompressed","RawCompressed","Raw"):
        if hasattr(pkobj, attr):
            priv = getattr(pkobj, attr)().ToBytes(); break
    if not priv or len(priv) < 32:
        die("could not extract 32-byte seed from bip_utils")
    seed32 = priv[:32]
    try:
        return Keypair.from_seed(seed32)
    except Exception:
        import nacl.signing as ns
        sk = ns.SigningKey(seed32)
        sec64 = sk.encode() + sk.verify_key.encode()
        return Keypair.from_bytes(sec64)

def load_signer_from_file(path: str) -> Keypair:
    # JSON id.json first
    try:
        obj = json.load(open(path, "r", encoding="utf-8"))
        if isinstance(obj, list):   # id.json array
            return Keypair.from_bytes(bytes(obj))
        if isinstance(obj, dict) and "secretKey" in obj:
            return Keypair.from_bytes(bytes(obj["secretKey"]))
    except Exception:
        pass
    # key=value
    kv = parse_signer_txt(path)
    mn = kv.get("mnemonic") or kv.get("phrase")
    if mn: return derive_from_mnemonic(mn, kv.get("passphrase",""))
    sec = kv.get("base58") or kv.get("secret") or kv.get("private")
    if sec: return keypair_from_base58(sec)
    # raw base58
    try: return keypair_from_base58(open(path,"r",encoding="utf-8").read().strip())
    except Exception as e: die(f"cannot load signer from '{path}': {e}")

# ----------------------- SPL helpers -----------------------
def ata(owner: Pubkey, mint: Pubkey) -> Pubkey:
    seeds = [bytes(owner), bytes(SPL_TOKEN_PROGRAM), bytes(mint)]
    return Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROG)[0]

def account_exists(pub: Pubkey) -> bool:
    try:
        res = rpc("getAccountInfo", [str(pub), {"encoding":"base64","commitment":"confirmed"}])
        return bool(res.get("value"))
    except Exception:
        return False

def create_ata_ix(payer: Pubkey, owner: Pubkey, mint: Pubkey, ata_addr: Pubkey) -> Instruction:
    metas = [
        AccountMeta(payer, True,  True),
        AccountMeta(ata_addr, False, True),
        AccountMeta(owner,   False, False),
        AccountMeta(mint,    False, False),
        AccountMeta(SYSTEM_PROGRAM, False, False),
        AccountMeta(SPL_TOKEN_PROGRAM, False, False),
        AccountMeta(Pubkey.from_string("SysvarRent111111111111111111111111111111111"), False, False),
    ]
    return Instruction(ASSOCIATED_TOKEN_PROG, b"", metas)

def get_mint_decimals(mint_str: str) -> int:
    if mint_str == USDC_MINT:
        return 6
    try:
        res = rpc("getAccountInfo", [mint_str, {"encoding":"jsonParsed","commitment":"confirmed"}])
        v = res.get("value") or {}
        parsed = (v.get("data") or {}).get("parsed") or {}
        info = parsed.get("info") or {}
        d = info.get("decimals")
        return int(d) if d is not None else 9
    except Exception:
        return 9

def resolve_mint_token(token: str) -> str:
    u = (token or "").strip().upper()
    if u == "SOL":  return SOL_MINT
    if u == "USDC": return USDC_MINT
    return extract_pubkey(token)

# ----------------------- main send -----------------------
def main():
    if RECIPIENT == "paste_the_destination_here":
        die("EDIT CONFIG: set RECIPIENT to a valid base58 address")

    mint_str = resolve_mint_token(TOKEN)
    if mint_str != SOL_MINT:
        fail_if_bad_base58("mint", mint_str)

    to_norm  = extract_pubkey(RECIPIENT)
    fail_if_bad_base58("recipient", to_norm)

    mint_pub = Pubkey.from_string(mint_str) if mint_str != SOL_MINT else None
    dest     = Pubkey.from_string(to_norm)

    # load signer
    kp = load_signer_from_file(SIGNER_FILE)
    payer = kp.pubkey()
    print(f"Signer: {payer}")
    print(f"To    : {dest}")
    print(f"Mint  : {mint_str if mint_str==SOL_MINT else mint_pub}")

    # decimals + atoms
    if mint_str == SOL_MINT:   decimals = 9
    elif mint_str == USDC_MINT:decimals = 6
    else:                      decimals = get_mint_decimals(mint_str)
    amount_atoms = int(round(float(AMOUNT_UI) * (10 ** decimals)))
    if amount_atoms <= 0: die("Amount too small for this token")
    print(f"Amount: {AMOUNT_UI} (atoms={amount_atoms}) decimals={decimals}")

    # existence checks for ATAs
    ixs: List[Instruction] = []
    ixs.append(set_compute_unit_limit(CU_LIMIT))
    ixs.append(set_compute_unit_price(CU_PRICE))

    src_ata = None
    dest_ata = None

    if mint_str == SOL_MINT:
        # SOL transfer
        data = b"\x02" + amount_atoms.to_bytes(8, "little")   # SystemProgram::Transfer (tag=2)
        ixs.append(Instruction(SYSTEM_PROGRAM, data, [
            AccountMeta(payer, True, True),
            AccountMeta(dest,  False, True),
        ]))
    else:
        src_ata  = ata(payer, mint_pub)
        dest_ata = ata(dest,  mint_pub)
        src_exists  = account_exists(src_ata)
        dest_exists = account_exists(dest_ata)

        if not src_exists:
            ixs.append(create_ata_ix(payer, payer, mint_pub, src_ata))
        if not dest_exists:
            ixs.append(create_ata_ix(payer, dest,  mint_pub, dest_ata))

        # SPL Token TransferChecked (tag 12): [u64 amount, u8 decimals]
        data = bytes([12]) + amount_atoms.to_bytes(8, "little") + bytes([decimals])
        ixs.append(Instruction(
            SPL_TOKEN_PROGRAM, data,
            [
                AccountMeta(src_ata,  False, True),
                AccountMeta(mint_pub, False, False),
                AccountMeta(dest_ata, False, True),
                AccountMeta(payer,    True,  False),
            ]
        ))

    # ---- Preflight: fee & rent, ensure payer SOL is enough ----
    # Prepare a message for fee estimation (needs a real blockhash)
    bh_for_fee = recent_blockhash()
    msg_for_fee = MessageV0.try_compile(payer, ixs, [], bh_for_fee)
    msg_b64 = base64.b64encode(to_bytes_versioned(msg_for_fee)).decode()
    fee_info = rpc("getFeeForMessage", [msg_b64, {"commitment":"finalized"}])
    fee_lamports = int(fee_info.get("value") or 5000)

    # Rent for ATAs (165 bytes each)
    rent_token_acct = get_min_rent_exempt(165)
    need_src = (src_ata is not None) and (not account_exists(src_ata))
    need_dst = (dest_ata is not None) and (not account_exists(dest_ata))
    rent_needed = (rent_token_acct if need_src else 0) + (rent_token_acct if need_dst else 0)

    balance = get_balance(payer)
    min_needed = fee_lamports + rent_needed + 50_000  # small buffer

    if balance < min_needed:
        need_sol = (min_needed - balance) / 1e9
        print(f"Insufficient SOL for fees/rent. Balance={balance/1e9:.6f} SOL, need ≥ {min_needed/1e9:.6f} SOL")
        print(f"→ Send at least {need_sol:.6f} SOL to {payer} and rerun.")
        sys.exit(2)

    # ---- Send ----
    bh  = recent_blockhash()
    msg = MessageV0.try_compile(payer, ixs, [], bh)
    tx  = VersionedTransaction(msg, [kp])
    raw = base64.b64encode(bytes(tx)).decode()

    try:
        sig = rpc("sendTransaction", [raw, {"encoding":"base64","skipPreflight": False, "maxRetries": 3}])
        print("Sent:", sig)
        print("Explorer:", f"https://solscan.io/tx/{sig}")
    except Exception as e:
        print("send failed:", e)
        try:
            sim = rpc("simulateTransaction", [raw, {"encoding":"base64","sigVerify": False}])
            print("simulate:", json.dumps(sim, indent=2))
        except Exception as ee:
            print("simulate failed:", ee)

# ----------------------- entry -----------------------
if __name__ == "__main__":
    if RECIPIENT == "paste_the_destination_here":
        die("EDIT CONFIG: set RECIPIENT to a valid base58 address")
    main()
