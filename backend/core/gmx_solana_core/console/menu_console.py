"""
GMX-Solana Interactive Console (menu-based, JSON-configured)

- Uses gmx_solana_console.json in repo root (no env required)
- Shows signer pubkey in the header (derived from 12-word mnemonic or base58 in file)
- Saves changes to JSON automatically

Menu:
  [1] RPC health
  [2] Set Store Program ID
  [3] Set Signer file path (re-derive pubkey)
  [4] Markets (paged)
  [5] Positions (from signer)
  [6] Positions (enter pubkey)
  [7] Set paging (limit/page/owner-offset)
  [0] Exit
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from ..config_loader import load_solana_config, pretty
from ..clients.solana_rpc_client import SolanaRpcClient, RpcError
from ..services.market_service import MarketService
from ..services.position_source_solana import SolanaPositionSource
from .config_io import load_json, save_json, DEFAULT_JSON

DEFAULT_CFG = Path(__file__).resolve().parent.parent / "config" / "solana.yaml"

def ensure_base58(s: str, label: str) -> None:
    import re
    if not isinstance(s, str) or len(s) < 32:
        raise ValueError(f"{label} looks invalid (too short).")
    if re.search(r"[^1-9A-HJ-NP-Za-km-z]", s):
        raise ValueError(f"{label} must be base58 (no 0,O,I,l or symbols).")

def derive_pubkey_from_signer(signer_path: Path) -> Optional[str]:
    """
    Try signer_loader → mnemonic → base58 in file.
    Mnemonic parser is tolerant: strips punctuation, lowercases, collapses whitespace.
    """
    # 1) project loader (as-is)
    try:
        from importlib import import_module
        sl = import_module("backend.services.signer_loader")
        for attr in ("load_wallet_pubkey","get_wallet_pubkey","wallet_pubkey","load_signer_pubkey"):
            if hasattr(sl, attr):
                try:
                    val = getattr(sl, attr)(str(signer_path))
                    if isinstance(val, str): return val
                except Exception: pass
        for attr in ("load_signer","get_signer","load_mnemonic","load_wallet"):
            if hasattr(sl, attr):
                try:
                    obj = getattr(sl, attr)(str(signer_path))
                    if hasattr(obj, "public_key"): return str(getattr(obj,"public_key"))
                    if hasattr(obj, "pubkey"):
                        pk = obj.pubkey()
                        return str(pk) if pk is not None else None
                    if isinstance(obj, str) and len(obj.split()) >= 12:
                        raw_mn = obj
                    else:
                        raw_mn = None
                except Exception:
                    raw_mn = None
            else:
                raw_mn = None
    except Exception:
        raw_mn = None

    # 2) read file if needed
    if signer_path.exists() and not raw_mn:
        raw_mn = signer_path.read_text(encoding="utf-8", errors="ignore")

    # 3) try tolerant mnemonic cleanup first
    if raw_mn:
        import re
        # keep letters/spaces only, lowercase, collapse spaces
        cleaned = re.sub(r"[^A-Za-z\s]", " ", raw_mn).lower()
        words = [w for w in cleaned.split() if w]
        # try common lengths in descending order
        for n in (24, 21, 18, 15, 12):
            if len(words) >= n:
                cand = " ".join(words[:n])
                try:
                    from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
                    Bip39MnemonicValidator(cand).Validate()
                    seed = Bip39SeedGenerator(cand).Generate()
                    ctx = Bip44.FromSeed(seed, Bip44Coins.SOLANA)
                    acct = ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                    return acct.PublicKey().ToAddress()
                except Exception:
                    continue  # try shorter length or fallback below

        # 4) scan for any base58 pubkey in the text
        tokens = re.findall(r"[1-9A-HJ-NP-Za-km-z]{32,}", raw_mn)
        for t in tokens:
            try:
                ensure_base58(t, "Wallet pubkey in signer file")
                return t
            except Exception:
                continue

    return None

def find_default_signer() -> Path:
    candidates = [
        Path.cwd() / "signer.txt",
        Path.cwd() / "signer",
        Path("C:/sonic7/signer"),
        Path.home() / "signer",
        Path.home() / "signer.txt",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]

class Session:
    def __init__(self):
        # precedence: JSON → YAML → env (we minimize env)
        j = load_json(DEFAULT_JSON)
        try:
            y = load_solana_config(str(DEFAULT_CFG))
        except Exception:
            y = {}

        self.rpc_http  = j.get("sol_rpc") or y.get("rpc_http") or os.environ.get("SOL_RPC") or ""
        self.store_pid = j.get("store_program_id") or (y.get("programs") or {}).get("store") or os.environ.get("GMSOL_STORE") or ""
        # signer file
        j_signer = j.get("signer_file")
        self.signer_file = Path(j_signer) if j_signer else find_default_signer()
        # options
        self.owner_offset = int(j.get("owner_offset") or 8)
        self.limit        = int(j.get("limit") or 100)
        self.page         = int(j.get("page") or 1)
        # derived
        self.signer_pubkey: Optional[str] = derive_pubkey_from_signer(self.signer_file)

    # persist all current session fields to JSON
    def persist(self):
        data: Dict[str, Any] = {
            "sol_rpc":         self.rpc_http,
            "store_program_id":self.store_pid,
            "signer_file":     str(self.signer_file),
            "owner_offset":    self.owner_offset,
            "limit":           self.limit,
            "page":            self.page,
        }
        save_json(data, DEFAULT_JSON)

    def rpc(self) -> SolanaRpcClient:
        return SolanaRpcClient(self.rpc_http)

    def header(self):
        print("="*72)
        print(" GMX-Solana Interactive Console ".center(72, " "))
        print("="*72)
        print(f" RPC        : {self.rpc_http or '(not set)'}")
        print(f" Store PID  : {self.store_pid or '(not set)'}")
        print(f" Signer File: {self.signer_file}")
        print(f" Signer Pub : {self.signer_pubkey or '(not derived)'}")
        print(f" OwnerOff   : {self.owner_offset}   Paging: limit={self.limit} page={self.page}")
        print(f" Config JSON: {DEFAULT_JSON}")
        print("-"*72)

    def input_b58(self, prompt: str, default: Optional[str]="") -> str:
        val = input(f"{prompt} [{default}]: ").strip() or (default or "")
        if val:
            ensure_base58(val, prompt)
        return val

def menu_loop(sess: Session):
    while True:
        sess.header()
        print("  [1] RPC health")
        print("  [2] Set Store Program ID")
        print("  [3] Set Signer file path (re-derive pubkey)")
        print("  [4] Markets (paged)")
        print("  [5] Positions (from signer)")
        print("  [6] Positions (enter pubkey)")
        print("  [7] Set paging (limit/page/owner-offset)")
        print("  [0] Exit")
        choice = input("Select: ").strip()

        try:
            if choice == "1":
                rpc = sess.rpc()
                try:  print(" health:", rpc.get_health())
                except RpcError as e: print(" getHealth error:", e)
                try:  print(" slot  :", rpc.get_slot())
                except RpcError as e: print(" getSlot error:", e)
                input("\n<enter>")

            elif choice == "2":
                sess.store_pid = sess.input_b58("Store Program ID", sess.store_pid)
                sess.persist()

            elif choice == "3":
                p = input(f"Signer file path [{sess.signer_file}]: ").strip()
                if p:
                    sess.signer_file = Path(p)
                sess.signer_pubkey = derive_pubkey_from_signer(sess.signer_file)
                if sess.signer_pubkey:
                    print("Derived signer pubkey:", sess.signer_pubkey)
                else:
                    print("⚠️  Could not derive signer pubkey from file.")
                sess.persist()
                input("\n<enter>")

            elif choice == "4":
                if not sess.store_pid:
                    print("⚠️  Set Store Program ID first (menu [2]).")
                else:
                    ms = MarketService(sess.rpc())
                    try:
                        out = ms.list_markets_basic(sess.store_pid, limit=sess.limit, page=sess.page)
                        print(pretty(out))
                    except Exception as e:
                        print("error:", e)
                input("\n<enter>")

            elif choice == "5":
                if not sess.store_pid:
                    print("⚠️  Set Store Program ID first (menu [2]).")
                else:
                    pub = sess.signer_pubkey or derive_pubkey_from_signer(sess.signer_file)
                    if not pub:
                        print(f"⚠️  Could not derive wallet from signer: {sess.signer_file}")
                    else:
                        try:
                            ensure_base58(pub, "Wallet pubkey")
                            src = SolanaPositionSource(sess.rpc())
                            out = src.list_open_positions_basic(
                                store_program=sess.store_pid,
                                wallet_b58=pub,
                                owner_offset=sess.owner_offset
                            )
                            print(pretty(out))
                        except Exception as e:
                            print("error:", e)
                input("\n<enter>")

            elif choice == "6":
                if not sess.store_pid:
                    print("⚠️  Set Store Program ID first (menu [2]).")
                else:
                    pub = sess.input_b58("Wallet pubkey", sess.signer_pubkey or "")
                    src = SolanaPositionSource(sess.rpc())
                    try:
                        out = src.list_open_positions_basic(
                            store_program=sess.store_pid,
                            wallet_b58=pub,
                            owner_offset=sess.owner_offset
                        )
                        print(pretty(out))
                    except Exception as e:
                        print("error:", e)
                input("\n<enter>")

            elif choice == "7":
                try:
                    sess.limit        = int(input(f"limit [{sess.limit}]: ").strip() or sess.limit)
                    sess.page         = int(input(f"page  [{sess.page }]: ").strip() or sess.page)
                    sess.owner_offset = int(input(f"owner offset [{sess.owner_offset}]: ").strip() or sess.owner_offset)
                    sess.persist()
                except Exception as e:
                    print("bad input:", e)
                input("\n<enter>")

            elif choice == "0":
                print("Bye."); return

        except KeyboardInterrupt:
            print("\nBye."); return
        except Exception as e:
            print("Unhandled error:", e)
            input("\n<enter>")

def main():
    sess = Session()
    if not sess.rpc_http:
        print("⚠️  No RPC endpoint configured. Set sol_rpc in gmx_solana_console.json and restart.")
        return 2
    menu_loop(sess)
    return 0

if __name__ == "__main__":
    sys.exit(main())
