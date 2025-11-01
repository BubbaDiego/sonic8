"""
GMX-Solana Interactive Console (menu-based)
- No tedious flags. Numbered options.
- Keeps session state (RPC, Store PID, signer path, owner offset).
- Minimal network deps (stdlib + bip-utils for mnemonic derivation).

Hotkeys:
  [1] RPC health
  [2] Set Store Program ID
  [3] Set Signer file path
  [4] Markets (paged)
  [5] Positions (from signer)
  [6] Positions (enter pubkey)
  [7] Set paging (limit/page)
  [0] Exit
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional

from ..config_loader import load_solana_config
from ..clients.solana_rpc_client import SolanaRpcClient, RpcError
from ..services.market_service import MarketService
from ..services.position_source_solana import SolanaPositionSource

DEFAULT_CFG = Path(__file__).resolve().parent.parent / "config" / "solana.yaml"

def ensure_base58(s: str, label: str) -> None:
    import re
    if not isinstance(s, str) or len(s) < 32:
        raise ValueError(f"{label} looks invalid (too short).")
    if re.search(r"[^1-9A-HJ-NP-Za-km-z]", s):
        raise ValueError(f"{label} must be base58 (no 0,O,I,l or symbols).")

def derive_pubkey_from_signer(signer_path: Path) -> Optional[str]:
    """
    Try: backend.services.signer_loader → BIP39 mnemonic (m/44'/501'/0'/0') → base58 in file.
    """
    # 1) project loader
    try:
        from importlib import import_module
        sl = import_module("backend.services.signer_loader")
        for attr in ("load_wallet_pubkey","get_wallet_pubkey","wallet_pubkey","load_signer_pubkey"):
            if hasattr(sl, attr):
                try:
                    val = getattr(sl, attr)(str(signer_path))
                    if isinstance(val, str):
                        return val
                except Exception:
                    pass
        for attr in ("load_signer","get_signer","load_mnemonic","load_wallet"):
            if hasattr(sl, attr):
                try:
                    obj = getattr(sl, attr)(str(signer_path))
                    if hasattr(obj, "public_key"):
                        return str(getattr(obj,"public_key"))
                    if hasattr(obj, "pubkey"):
                        pk = obj.pubkey()
                        return str(pk) if pk is not None else None
                    if isinstance(obj, str) and len(obj.split()) >= 12:
                        txt = obj
                    else:
                        txt = None
                except Exception:
                    txt = None
            else:
                txt = None
    except Exception:
        txt = None

    # 2) read file if needed
    if signer_path.exists() and not txt:
        txt = signer_path.read_text(encoding="utf-8").strip()

    # 3) mnemonic?
    if txt:
        words = txt.split()
        if len(words) in (12, 15, 18, 21, 24):
            try:
                from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
                Bip39MnemonicValidator(txt).Validate()
                seed = Bip39SeedGenerator(txt).Generate()
                ctx = Bip44.FromSeed(seed, Bip44Coins.SOLANA)
                acct = ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                return acct.PublicKey().ToAddress()
            except Exception:
                pass

        # 4) scan for base58 pubkey
        import re
        tokens = re.findall(r"[1-9A-HJ-NP-Za-km-z]{32,}", txt)
        for t in tokens:
            try:
                ensure_base58(t, "Wallet pubkey in signer file")
                return t
            except Exception:
                continue

    return None

class Session:
    def __init__(self):
        # cfg
        try:
            cfg = load_solana_config(str(DEFAULT_CFG))
        except Exception as e:
            print(f"⚠️  Config load failed: {e}")
            cfg = {}
        self.rpc_http = cfg.get("rpc_http") or os.environ.get("SOL_RPC") or ""
        self.store_pid = (cfg.get("programs") or {}).get("store") or os.environ.get("GMSOL_STORE") or ""
        # defaults
        self.signer_file = (Path.cwd() / "signer.txt")
        if not self.signer_file.exists():
            alt = Path.cwd() / "signer"
            if alt.exists():
                self.signer_file = alt
        self.owner_offset = 8
        self.limit = 100
        self.page = 1
        self.verbose = False

    def rpc(self) -> SolanaRpcClient:
        return SolanaRpcClient(self.rpc_http)

    def header(self):
        print("="*72)
        print(" GMX-Solana Interactive Console ".center(72, " "))
        print("="*72)
        print(f" RPC      : {self.rpc_http or '(not set)'}")
        print(f" Store PID: {self.store_pid or '(not set)'}")
        print(f" Signer   : {self.signer_file}")
        print(f" OwnerOff : {self.owner_offset}   Paging: limit={self.limit} page={self.page}")
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
        print("  [3] Set Signer file path")
        print("  [4] Markets (paged)")
        print("  [5] Positions (from signer)")
        print("  [6] Positions (enter pubkey)")
        print("  [7] Set paging (limit/page)")
        print("  [0] Exit")
        choice = input("Select: ").strip()

        try:
            if choice == "1":
                rpc = sess.rpc()
                try:
                    print(" health:", rpc.get_health())
                except RpcError as e:
                    print(" getHealth error:", e)
                try:
                    print(" slot  :", rpc.get_slot())
                except RpcError as e:
                    print(" getSlot error:", e)
                input("\n<enter>")

            elif choice == "2":
                sess.store_pid = sess.input_b58("Store Program ID", sess.store_pid)

            elif choice == "3":
                p = input(f"Signer file path [{sess.signer_file}]: ").strip()
                if p:
                    sess.signer_file = Path(p)

            elif choice == "4":
                if not sess.store_pid:
                    print("⚠️  Set Store Program ID first (menu [2]).")
                else:
                    ms = MarketService(sess.rpc())
                    try:
                        out = ms.list_markets_basic(sess.store_pid, limit=sess.limit, page=sess.page)
                        from ..config_loader import pretty
                        print(pretty(out))
                    except Exception as e:
                        print("error:", e)
                input("\n<enter>")

            elif choice == "5":
                if not sess.store_pid:
                    print("⚠️  Set Store Program ID first (menu [2]).")
                else:
                    pub = derive_pubkey_from_signer(sess.signer_file)
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
                            from ..config_loader import pretty
                            print(pretty(out))
                        except Exception as e:
                            print("error:", e)
                input("\n<enter>")

            elif choice == "6":
                if not sess.store_pid:
                    print("⚠️  Set Store Program ID first (menu [2]).")
                else:
                    pub = sess.input_b58("Wallet pubkey")
                    src = SolanaPositionSource(sess.rpc())
                    try:
                        out = src.list_open_positions_basic(
                            store_program=sess.store_pid,
                            wallet_b58=pub,
                            owner_offset=sess.owner_offset
                        )
                        from ..config_loader import pretty
                        print(pretty(out))
                    except Exception as e:
                        print("error:", e)
                input("\n<enter>")

            elif choice == "7":
                try:
                    sess.limit = int(input(f"limit [{sess.limit}]: ").strip() or sess.limit)
                    sess.page  = int(input(f"page  [{sess.page }]: ").strip() or sess.page)
                    sess.owner_offset = int(input(f"owner offset [{sess.owner_offset}]: ").strip() or sess.owner_offset)
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
    # wire RPC from ENV or config
    if not os.environ.get("SOL_RPC"):
        print("ℹ️  SOL_RPC not set; using value from config if present.")
    sess = Session()
    if not sess.rpc_http:
        print("⚠️  No RPC endpoint configured. Set $env:SOL_RPC and restart.")
        return 2
    menu_loop(sess)
    return 0

if __name__ == "__main__":
    sys.exit(main())
