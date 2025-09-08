# v1.1 – CLI + interactive fallback
import os, sys, json, base64, re, argparse
from pathlib import Path
from typing import Optional, List

# deps: pip install bip-utils pynacl base58 python-dotenv
from dotenv import load_dotenv
import base58, nacl.signing
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes, Bip32Slip10Ed25519

IC_OK="✅"; IC_X="❌"; IC_Q="❓"; IC_K="🔐"; IC_W="👛"; IC_I="ℹ️"

def to_pub58(priv: bytes) -> str:
    sk = nacl.signing.SigningKey(priv)
    return base58.b58encode(sk.verify_key.encode()).decode()

def priv64_from_any(s: str) -> Optional[bytes]:
    s = s.strip().strip('"').strip("'")
    if not s: return None
    # JSON array
    if s.startswith("[") and s.endswith("]"):
        try:
            b = bytes(json.loads(s))
            return b if len(b)==64 else nacl.signing.SigningKey(b).encode()
        except: pass
    # b64
    try:
        b = base64.b64decode(s, validate=True)
        return b if len(b)==64 else nacl.signing.SigningKey(b).encode()
    except: pass
    # b58
    try:
        b = base58.b58decode(s)
        return b if len(b)==64 else nacl.signing.SigningKey(b).encode()
    except: pass
    # hex
    try:
        b = bytes.fromhex(s)
        return b if len(b)==64 else nacl.signing.SigningKey(b).encode()
    except: pass
    return None

def seed_from_mnemonic(mnemonic: str, bip39_pw: str="") -> bytes:
    return Bip39SeedGenerator(mnemonic, lang=None).Generate(bip39_pw)

def derive_account(seed: bytes, account_idx: int, change: int) -> bytes:
    ctx = (Bip44.FromSeed(seed, Bip44Coins.SOLANA)
           .Purpose().Coin().Account(account_idx)
           .Change(Bip44Changes.CHAIN_EXT if change==0 else Bip44Changes.CHAIN_INT)
           .AddressIndex(0))
    return ctx.PrivateKey().Raw().ToBytes()

def derive_address(seed: bytes, addr_idx: int, change: int) -> bytes:
    ctx = (Bip44.FromSeed(seed, Bip44Coins.SOLANA)
           .Purpose().Coin().Account(0)
           .Change(Bip44Changes.CHAIN_EXT if change==0 else Bip44Changes.CHAIN_INT)
           .AddressIndex(addr_idx))
    return ctx.PrivateKey().Raw().ToBytes()

def derive_custom(seed: bytes, path: str) -> bytes:
    node = Bip32Slip10Ed25519.FromSeed(seed).DerivePath(path)
    return node.PrivateKey().Raw().ToBytes()

def search_target(seed: bytes, target: str, max_account: int, max_addr: int, changes: List[int]):
    # account-index sweep
    for ch in changes:
        for acc in range(max_account+1):
            if to_pub58(derive_account(seed, acc, ch)) == target:
                return ("account", acc, ch)
    # address-index sweep
    for ch in changes:
        for adr in range(max_addr+1):
            if to_pub58(derive_address(seed, adr, ch)) == target:
                return ("address", adr, ch)
    return None

def write_env(path: Path, key: str, value: str):
    txt = ""
    if path.exists():
        txt = path.read_text(encoding="utf-8", errors="ignore")
        pattern = re.compile(rf"^{re.escape(key)}=.*$", flags=re.MULTILINE)
        if pattern.search(txt):
            txt = pattern.sub(f"{key}={value}", txt)
        else:
            txt = (txt.rstrip() + "\n" + f"{key}={value}\n")
    else:
        txt = f"{key}={value}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(txt, encoding="utf-8")

def project_env_path() -> Path:
    here = Path(__file__).resolve()
    root_env = here.parents[2] / ".env"
    return root_env if root_env.parent.exists() else (Path.cwd() / ".env")

def print_result(priv: bytes, label: str, write_env_flag: bool):
    pub = to_pub58(priv)
    sec64 = base64.b64encode(nacl.signing.SigningKey(priv).encode()).decode()
    print(f"{IC_OK} {label}\n{IC_W} Public Key: {pub}\n{IC_K} Secret (base64): {sec64}")
    if write_env_flag:
        p = project_env_path()
        write_env(p, "WALLET_SECRET_BASE64", sec64)
        print(f"{IC_OK} Wrote WALLET_SECRET_BASE64 to {p}")

def parse_args():
    load_dotenv(override=True)
    ap = argparse.ArgumentParser(description="Derive or import a Solana key and emit base64 for .env")
    # direct secret
    ap.add_argument("--secret", help="Phantom JSON array or base58/base64/hex 64-byte secret")
    # mnemonic flows
    ap.add_argument("--mnemonic", help="12/24 words")
    ap.add_argument("--bip39-pass", default="", help="Optional BIP39 passphrase")
    ap.add_argument("--mode", choices=["account","address","custom","search"], help="Derivation mode")
    ap.add_argument("--index", type=int, help="account-index (mode=account) OR address-index (mode=address)")
    ap.add_argument("--change", type=int, default=0, help="0 (external) or 1 (internal)")
    ap.add_argument("--path", help="custom hardened path for mode=custom (e.g., m/44'/501'/0'/0')")
    ap.add_argument("--target", help="target address for mode=search")
    ap.add_argument("--max-account", type=int, default=100)
    ap.add_argument("--max-addr", type=int, default=400)
    ap.add_argument("--changes", default="0,1", help="comma sep list for search, default 0,1")
    ap.add_argument("--write-env", action="store_true", help="Write WALLET_SECRET_BASE64 into project .env")
    args = ap.parse_args()
    return args

def main():
    args = parse_args()

    # 1) direct secret path
    if args.secret:
        b = priv64_from_any(args.secret)
        if not b:
            print(f"{IC_X} Could not parse --secret"); sys.exit(1)
        print_result(b, "Loaded direct secret", args.write_env); return

    # 2) mnemonic paths or interactive fallback
    mn = (args.mnemonic or "").strip().strip('"').strip("'")
    if not mn:
        # interactive fallback if we have a TTY
        if sys.stdin.isatty():
            print(f"{IC_I} No flags given. Enter mnemonic flow.")
            mn = input(f"{IC_Q}  Enter 12/24 words: ").strip()
            if not mn: print(f"{IC_X} Empty mnemonic."); sys.exit(1)
            mode = input("Mode [account/address/custom/search] (default account): ").strip() or "account"
            args.mode = mode
            if mode in ("account","address"):
                args.index = int(input("Index (e.g., 0,1,2…): ").strip())
                ch = input("Change (0 or 1) [0]: ").strip()
                args.change = int(ch) if ch else 0
            elif mode == "custom":
                args.path = input("Path (e.g., m/44'/501'/0'/0'): ").strip()
            else:
                args.target = input("Target address to find: ").strip()
        else:
            print(f"{IC_X} No stdin and no flags. Use --secret OR --mnemonic + --mode …"); sys.exit(2)

    seed = seed_from_mnemonic(mn, args.bip39_pass)

    if args.mode == "account":
        if args.index is None: print(f"{IC_X} --index required for mode=account"); sys.exit(2)
        priv = derive_account(seed, args.index, args.change)
        print_result(priv, f"Derived m/44'/501'/{args.index}'/{args.change}'/0", args.write_env)
    elif args.mode == "address":
        if args.index is None: print(f"{IC_X} --index required for mode=address"); sys.exit(2)
        priv = derive_address(seed, args.index, args.change)
        print_result(priv, f"Derived m/44'/501'/0'/{args.change}'/{args.index}", args.write_env)
    elif args.mode == "custom":
        if not args.path: print(f"{IC_X} --path required for mode=custom"); sys.exit(2)
        priv = derive_custom(seed, args.path)
        print_result(priv, f"Derived from {args.path}", args.write_env)
    elif args.mode == "search":
        if not args.target: print(f"{IC_X} --target required for mode=search"); sys.exit(2)
        changes = [int(x) for x in re.split(r"[,\s]+", args.changes) if x!=""]
        hit = search_target(seed, args.target, args.max_account, args.max_addr, changes)
        if not hit:
            print(f"{IC_X} Not found within account[0..{args.max_account}] × addr[0..{args.max_addr}] × change{changes}")
            sys.exit(1)
        variant, idx, ch = hit
        if variant == "account":
            priv = derive_account(seed, idx, ch)
            label = f"Derived m/44'/501'/{idx}'/{ch}'/0  (found by search)"
        else:
            priv = derive_address(seed, idx, ch)
            label = f"Derived m/44'/501'/0'/{ch}'/{idx}  (found by search)"
        print_result(priv, label, args.write_env)
    else:
        print(f"{IC_X} --mode required (account/address/custom/search)"); sys.exit(2)

if __name__ == "__main__":
    main()
