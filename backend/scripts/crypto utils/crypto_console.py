# crypto_console.py — INTERACTIVE CONSOLE UI (menu-driven, no flags required)
# Works on Windows CMD/PowerShell. If launched from a non-interactive runner,
# it auto-spawns a real console window and keeps it open.
#
# Dependencies (inside your venv):
#   pip install python-dotenv bip-utils pynacl base58 httpx solders solana
#
# Secure: never prints secrets; only public keys. Secrets are edited *inside* this console, not via CLI args.

import os
import sys
import json
import re
import base64
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple, Dict

from dotenv import load_dotenv
import base58, nacl.signing

try:
    from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
    HAVE_MNEMONIC = True
except Exception:
    HAVE_MNEMONIC = False

# Icons
IC_OK="✅"; IC_X="❌"; IC_W="👛"; IC_RPC="🌐"; IC_TX="🔎"; IC_SOL="◎"; IC_USD="💵"; IC_MNU="📟"; IC_KEY="🔐"; IC_ENV="🗂️"

# ──────────────────────────────────────────────────────────────────────────────
# Spawn real console if run without a TTY (IDE runners, schedulers, etc.)
# ──────────────────────────────────────────────────────────────────────────────
def ensure_console():
    if sys.stdin.isatty():
        return
    if os.name == "nt":
        py = sys.executable
        me = os.path.abspath(__file__)
        CREATE_NEW_CONSOLE = 0x00000010
        subprocess.Popen([py, me], creationflags=CREATE_NEW_CONSOLE)
        sys.exit(0)
    else:
        print("This UI needs a real terminal. Run in a shell:")
        print(f"  {sys.executable} {__file__}")
        sys.exit(2)

# ──────────────────────────────────────────────────────────────────────────────
# .env handling — ALWAYS prefer top-level sonic5\.env (or override via CRYPTO_ENV_PATH)
# Robust parser that ignores commented lines and treats empty values as absent.
# ──────────────────────────────────────────────────────────────────────────────
_ENV_CACHE: Optional[Path] = None

def find_env_path() -> Path:
    """Resolve project .env deterministically."""
    global _ENV_CACHE
    if _ENV_CACHE is not None:
        return _ENV_CACHE

    override = os.getenv("CRYPTO_ENV_PATH", "").strip().strip('"').strip("'")
    if override and Path(override).exists():
        _ENV_CACHE = Path(override)
        return _ENV_CACHE

    here = Path(__file__).resolve()
    # Prefer parent named 'sonic5'
    for parent in here.parents:
        if parent.name.lower() == "sonic5":
            env = parent / ".env"
            if env.exists():
                _ENV_CACHE = env
                return env
    # Otherwise, pick highest ancestor .env
    candidates = [p / ".env" for p in here.parents if (p / ".env").exists()]
    if candidates:
        _ENV_CACHE = candidates[-1]
        return _ENV_CACHE
    _ENV_CACHE = Path.cwd() / ".env"
    return _ENV_CACHE

def parse_env_file(path: Path) -> Dict[str,str]:
    """Minimal .env parser: KEY=VALUE, ignore blank and #comment lines. Trim quotes. Empty values removed."""
    out: Dict[str,str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k,v = line.split("=",1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if v == "":
            # treat empty as absent
            continue
        out[k] = v
    return out

def write_env(key: str, value: Optional[str]):
    """Set or delete a key in the chosen .env."""
    p = find_env_path()
    kv = parse_env_file(p)
    if value is None:
        kv.pop(key, None)
    else:
        kv[key] = value
    # Rebuild file deterministically
    lines = []
    # Keep order stable: put signer vars first, then others alpha
    signer_order = ["WALLET_SECRET_BASE64","MNEMONIC","MNEMONIC_INDEX","FORCE_SIGNER_SOURCE","RPC_URL"]
    used = set()
    for k in signer_order:
        if k in kv:
            lines.append(f"{k}={kv[k]}")
            used.add(k)
    for k in sorted(kv.keys()):
        if k not in used:
            lines.append(f"{k}={kv[k]}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p

def sync_env_to_file():
    """Ensure process env reflects *only* what’s in the chosen .env (for signer vars)."""
    p = find_env_path()
    kv = parse_env_file(p)
    # scrub
    for k in ("WALLET_SECRET_BASE64","MNEMONIC","MNEMONIC_INDEX","FORCE_SIGNER_SOURCE","RPC_URL"):
        if k not in kv:
            os.environ.pop(k, None)
    # load chosen .env fresh
    load_dotenv(override=False)                   # base
    load_dotenv(dotenv_path=p, override=True)    # chosen file

# ──────────────────────────────────────────────────────────────────────────────
# Utils
# ──────────────────────────────────────────────────────────────────────────────
def pyexe() -> str: return sys.executable
def scripts_dir() -> Path: return Path(__file__).resolve().parent
def short(s: str, L=6, R=6) -> str: return s if len(s) <= (L+R) else f"{s[:L]}…{s[-R:]}"
def pause(): input("\nPress Enter to continue...")

def yesno(msg: str, default=False) -> bool:
    y = "Y/n" if default else "y/N"
    ans = input(f"{msg} [{y}]: ").strip().lower()
    return (ans == "" and default) or ans.startswith("y")

def parse_secret_any(s: str) -> bytes:
    s2 = s.strip().strip('"').strip("'")
    # JSON array
    if s2.startswith("[") and s2.endswith("]"):
        b = bytes(json.loads(s2));  return b if len(b)==64 else nacl.signing.SigningKey(b).encode()
    # base64
    try:
        b = base64.b64decode(s2, validate=True); return b if len(b)==64 else nacl.signing.SigningKey(b).encode()
    except Exception: pass
    # base58
    try:
        b = base58.b58decode(s2);  return b if len(b)==64 else nacl.signing.SigningKey(b).encode()
    except Exception: pass
    # hex
    try:
        b = bytes.fromhex(s2);     return b if len(b)==64 else nacl.signing.SigningKey(b).encode()
    except Exception: pass
    raise ValueError("Could not parse secret (expect JSON[64], base58/base64/hex)")

def to_pub58(priv: bytes) -> str:
    return base58.b58encode(nacl.signing.SigningKey(priv).verify_key.encode()).decode()

def run_script(name: str, args: List[str]):
    path = scripts_dir() / name
    if not path.exists():
        print(f"{IC_X} missing script: {path}")
        return 1
    cmd = [pyexe(), str(path)] + args
    print(f"\n→ {' '.join(cmd)}\n")
    return subprocess.call(cmd)

# ──────────────────────────────────────────────────────────────────────────────
# Signer banner
# ──────────────────────────────────────────────────────────────────────────────
def current_signer_info() -> Tuple[str, Optional[str]]:
    """
    Returns (source, pubkey_or_None)
    Source logic:
      - If FORCE_SIGNER_SOURCE=MNEMONIC, ignore WALLET_SECRET_BASE64
      - Else if WALLET_SECRET_BASE64 present & decodes: use it
      - Else if MNEMONIC + MNEMONIC_INDEX present: derive pubkey
      - Else: none
    """
    p = find_env_path()
    kv = parse_env_file(p)
    force = (kv.get("FORCE_SIGNER_SOURCE","").strip().upper() == "MNEMONIC")

    if not force:
        wsb64 = kv.get("WALLET_SECRET_BASE64","").strip()
        if wsb64:
            try:
                priv = base64.b64decode(wsb64)
                return ("WALLET_SECRET_BASE64", to_pub58(priv))
            except Exception:
                pass

    mn = kv.get("MNEMONIC","").strip().strip('"').strip("'")
    idx = kv.get("MNEMONIC_INDEX", "").strip()
    if mn and idx and HAVE_MNEMONIC:
        try:
            i = int(idx)
            seed = Bip39SeedGenerator(mn).Generate()
            ctx = (Bip44.FromSeed(seed, Bip44Coins.SOLANA)
                   .Purpose().Coin().Account(i).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0))
            return (f"MNEMONIC_INDEX={i}", to_pub58(ctx.PrivateKey().Raw().ToBytes()))
        except Exception:
            pass
    return ("(none)", None)

def signer_banner():
    envp = find_env_path()
    print(f"{IC_ENV} .env: {envp}")
    src, pub = current_signer_info()
    if pub:
        print(f"{IC_KEY} Signer: {pub}  (source={src})")
    else:
        print(f"{IC_KEY} Signer: (not configured)  — use menu 3 to import/derive")

# ──────────────────────────────────────────────────────────────────────────────
# Menus
# ──────────────────────────────────────────────────────────────────────────────
def menu_balances():
    signer_banner()
    use_signer = yesno("Use current signer from .env?", True)
    if use_signer:
        src, pub = current_signer_info()
        if not pub:
            print("❌ No signer configured. Use menu 3 to import/derive first."); pause(); return
        rc = run_script("wallet_balances.py", ["--pubkey", pub])
    else:
        pk = input("Enter address (base58): ").strip()
        if not pk:
            print("❌ address required"); pause(); return
        rc = run_script("wallet_balances.py", ["--pubkey", pk])
    if rc != 0: print(f"❌ balances exited with {rc}")
    pause()

def menu_balances_many():
    signer_banner()
    s = input("Paste addresses (comma/space/newline separated):\n").strip()
    addrs = re.split(r"[,\s]+", s)
    addrs = [a for a in addrs if a]
    if not addrs:
        print(f"{IC_X} no addresses"); pause(); return
    rc = run_script("balances_bulk.py", ["--addresses", ",".join(addrs)])
    if rc != 0: print(f"{IC_X} balances-many exited with {rc}")
    pause()

def menu_import_secret():
    print("\nChoose:\n  1) Paste private key (base58/base64/hex or JSON array)\n  2) Derive from mnemonic\n  3) Remove WALLET_SECRET_BASE64 (force mnemonic)\n  4) Force signer = MNEMONIC (toggle)")
    ch = input("> ").strip() or "1"

    if ch == "3":
        p = write_env("WALLET_SECRET_BASE64", None)
        print(f"{IC_OK} Removed WALLET_SECRET_BASE64 from {p}"); pause(); return
    if ch == "4":
        p = find_env_path()
        kv = parse_env_file(p)
        cur = kv.get("FORCE_SIGNER_SOURCE","").strip().upper()
        new = "MNEMONIC" if cur != "MNEMONIC" else None
        p = write_env("FORCE_SIGNER_SOURCE", new)
        print(f"{IC_OK} FORCE_SIGNER_SOURCE set to {new or '(cleared)'} in {p}"); pause(); return

    if ch == "1":
        sec = input("Paste private key: ").strip()
        try:
            b = parse_secret_any(sec)
        except Exception as e:
            print(f"{IC_X} {e}"); pause(); return
        pub = to_pub58(b)
        sec64 = base64.b64encode(nacl.signing.SigningKey(b).encode()).decode()
        if yesno(f"{IC_OK} Parsed secret for {pub}. Write WALLET_SECRET_BASE64 to .env?", True):
            p = write_env("WALLET_SECRET_BASE64", sec64); print(f"{IC_OK} wrote {short(str(p))}")
        else:
            print(f"{IC_W} Public: {pub}\nbase64: {sec64}")
        pause(); return

    # Derive from mnemonic
    if not HAVE_MNEMONIC:
        print("❌ bip-utils/pynacl not installed. pip install bip-utils pynacl"); pause(); return
    mnemonic = input("Paste 12/24 words: ").strip().strip('"').strip("'")
    if not mnemonic:
        print("❌ empty mnemonic"); pause(); return
    mode = input("Derivation mode [account/address] (default account): ").strip().lower() or "account"
    try:
        idx = int(input("Index (0,1,2…): ").strip())
    except Exception:
        print("❌ invalid index"); pause(); return
    chg = input("Change (0=external, 1=internal) [0]: ").strip()
    chg = int(chg) if chg else 0

    seed = Bip39SeedGenerator(mnemonic).Generate()
    if mode.startswith("acc"):
        ctx = (Bip44.FromSeed(seed, Bip44Coins.SOLANA).Purpose().Coin().Account(idx)
               .Change(Bip44Changes.CHAIN_EXT if chg==0 else Bip44Changes.CHAIN_INT).AddressIndex(0))
    else:
        ctx = (Bip44.FromSeed(seed, Bip44Coins.SOLANA).Purpose().Coin().Account(0)
               .Change(Bip44Changes.CHAIN_EXT if chg==0 else Bip44Changes.CHAIN_INT).AddressIndex(idx))
    priv = ctx.PrivateKey().Raw().ToBytes()
    pub = to_pub58(priv)
    sec64 = base64.b64encode(nacl.signing.SigningKey(priv).encode()).decode()
    if yesno(f"{IC_OK} Derived {pub}. Write WALLET_SECRET_BASE64 to .env?", True):
        p = write_env("WALLET_SECRET_BASE64", sec64); print(f"{IC_OK} wrote {short(str(p))}")
    else:
        print(f"{IC_W} Public: {pub}\nbase64: {sec64}")
    pause()

def menu_swap():
    signer_banner()
    print("\nSwap USDC ↔ SOL (Jupiter lite)")
    pair = input("Pair [1=USDC->SOL, 2=SOL->USDC] (default 1): ").strip() or "1"
    pair = "usdc->sol" if pair != "2" else "sol->usdc"
    amt  = input(f"Amount ({'USDC' if pair=='usdc->sol' else 'SOL'}): ").strip()
    if not amt: print("❌ amount required"); pause(); return
    sl   = input("Slippage bps [50]: ").strip() or "50"
    idxov= input("Override MNEMONIC_INDEX (blank=no): ").strip()
    args = ["--pair", pair, "--amount", amt, "--slippage-bps", sl]
    if idxov: args += ["--index", idxov]
    rc = run_script("jup_swap_to_sol.py", args)
    if rc != 0: print(f"❌ swap exited with {rc}")
    pause()

def menu_perps_open():
    signer_banner()
    print("\nPerps: open LONG SOL with USDC collateral")
    sz  = input("Size USD (e.g., 1): ").strip()
    col = input("Collateral USDC (e.g., 0.30): ").strip()
    mp  = input("Max price (USD) [1000]: ").strip() or "1000"
    if not sz or not col: print("❌ size & collateral required"); pause(); return
    rc = run_script("perps_open_long.py", ["--size-usd", sz, "--collateral-usdc", col, "--max-price", mp])
    if rc != 0: print(f"❌ perps open exited with {rc}")
    pause()

def menu_settings():
    sync_env_to_file()
    p = find_env_path()
    print(f"\n{IC_ENV} .env: {p}")
    data = parse_env_file(p)
    print("Keys present:", ", ".join(sorted(data.keys())) or "(none)")
    rpc = data.get("RPC_URL","https://api.mainnet-beta.solana.com")
    print(f"Current RPC: {rpc}")
    src, pub = current_signer_info()
    if pub: print(f"{IC_KEY} Active signer: {pub}  (source={src})")
    else:   print(f"{IC_KEY} Active signer: (not configured)")
    print("\nActions:")
    print(" 1) Change RPC")
    print(" 2) Remove WALLET_SECRET_BASE64")
    print(" 3) Toggle FORCE_SIGNER_SOURCE=MNEMONIC")
    print(" 0) Back")
    ch = input("> ").strip() or "0"
    if ch == "1":
        new = input("RPC URL: ").strip()
        if new: write_env("RPC_URL", new); print(f"{IC_OK} RPC updated")
    elif ch == "2":
        write_env("WALLET_SECRET_BASE64", None); print(f"{IC_OK} WALLET_SECRET_BASE64 removed")
    elif ch == "3":
        cur = data.get("FORCE_SIGNER_SOURCE","").strip().upper()
        write_env("FORCE_SIGNER_SOURCE", None if cur=="MNEMONIC" else "MNEMONIC")
        print(f"{IC_OK} FORCE_SIGNER_SOURCE set to {('cleared' if cur=='MNEMONIC' else 'MNEMONIC')}")
    pause()

# ──────────────────────────────────────────────────────────────────────────────
# Main loop
# ──────────────────────────────────────────────────────────────────────────────
def main():
    ensure_console()
    if os.name == "nt": os.system("chcp 65001 > nul")
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        sync_env_to_file()
        print(f"{IC_MNU}  Crypto Console — Sonic")
        signer_banner()
        print("\n 1) Balances")
        print(" 2) Balances (many)")
        print(" 3) Import signer (secret/mnemonic → .env)")
        print(" 4) Swap (USDC ↔ SOL)")
        print(" 5) Perps: Open LONG SOL")
        print(" 6) Settings (RPC / signer)")
        print(" 0) Exit")
        ch = input("> ").strip() or "1"
        try:
            if ch == "1": menu_balances()
            elif ch == "2": menu_balances_many()
            elif ch == "3": menu_import_secret()
            elif ch == "4": menu_swap()
            elif ch == "5": menu_perps_open()
            elif ch == "6": menu_settings()
            elif ch == "0": break
        except KeyboardInterrupt:
            print("\n(aborted)"); pause()
        except Exception as e:
            print(f"\n{IC_X} {e}"); pause()

if __name__ == "__main__":
    main()
