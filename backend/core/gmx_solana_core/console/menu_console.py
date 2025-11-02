"""
GMX-Solana Interactive Console (Option A: memcmp fast path)

- JSON at C:\\sonic7\\gmx_solana_console.json (no envs)
- Shows signer pubkey in header (derived or from JSON)
- Positions (from signer) via memcmp at owner_offset (default 24)
- NEW: [8] Sweep offsets (quick diagnostic)
- NEW: [9] Show first match (raw) to peek base64 data

Menu:
  [1] RPC health
  [2] Set Store Program ID
  [3] Set Signer file path (re-derive pubkey)
  [4] Markets (paged)
  [5] Positions (from signer)  ← memcmp at owner_offset
  [6] Positions (enter pubkey) ← memcmp at owner_offset
  [7] Set paging (limit/page/owner-offset)
  [8] Sweep offsets (0,8,16,24,32,40,48,56,64,72,80,96,112,128)
  [9] Show first match (raw)
  [0] Exit
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import json
import re

from ..clients.solana_rpc_client import SolanaRpcClient, RpcError
from ..services.position_source_solana import SolanaPositionSource
from ..services.market_service import MarketService
from ..config_loader import load_solana_config, pretty
from .config_io import load_json, save_json, DEFAULT_JSON
from ..services.memcmp_service import memcmp_count, memcmp_sweep, fetch_account_base64

DEFAULT_CFG = Path(__file__).resolve().parent.parent / "config" / "solana.yaml"

def ensure_base58(s: str, label: str) -> None:
    if not isinstance(s, str) or len(s) < 32 or re.search(r"[^1-9A-HJ-NP-Za-km-z]", s):
        raise ValueError(f"{label} must be base58 (>=32 chars, no 0,O,I,l).")

def derive_pubkey_from_signer(signer_path: Path) -> Optional[str]:
    """
    Prefer base58 pubkey anywhere in the file; else tolerant BIP39 12/15/18/21/24 words.
    """
    # Try base58 first
    if signer_path.exists():
        txt = signer_path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"[1-9A-HJ-NP-Za-km-z]{32,}", txt)
        if m:
            return m.group(0)
        # Try mnemonic
        try:
            from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator, Bip44, Bip39SeedError, Bip44Coins, Bip44Changes
            clean = re.sub(r"[^A-Za-z\s]", " ", txt).lower()
            words = [w for w in clean.split() if w]
            for n in (24,21,18,15,12):
                if len(words) >= n:
                    cand = " ".join(words[:n])
                    try:
                        Bip39MnemonicValidator(cand).Validate()
                        seed = Bip39SeedGenerator(cand).Generate()
                        ctx  = Bip44.FromSeed(seed, Bip44Coins.SOLANA)
                        acct = ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                        return acct.PublicKey().ToAddress()
                    except Exception:
                        continue
        except Exception:
            pass
    return None

def find_default_signer() -> Path:
    for p in [Path.cwd()/"signer.txt", Path.cwd()/"signer", Path("C:/sonic7/signer.txt"), Path("C:/sonic7/signer")]:
        if p.exists(): return p
    return Path("C:/sonic7/signer.txt")

class Session:
    def __init__(self):
        # JSON first
        j = load_json(DEFAULT_JSON)
        # YAML fallback
        try: y = load_solana_config(str(DEFAULT_CFG))
        except Exception: y = {}

        self.rpc_http  = j.get("sol_rpc") or y.get("rpc_http") or os.environ.get("SOL_RPC") or ""
        self.store_pid = j.get("store_program_id") or (y.get("programs") or {}).get("store") or os.environ.get("GMSOL_STORE") or ""
        self.signer_file = Path(j.get("signer_file") or "C:/sonic7/signer.txt")
        if not self.signer_file.exists():
            self.signer_file = find_default_signer()
        self.owner_offset = int(j.get("owner_offset") or 24)  # default 24 for GMX hits you found
        self.limit        = int(j.get("limit") or 100)
        self.page         = int(j.get("page") or 1)
        self.signer_pubkey: Optional[str] = j.get("signer_pubkey") or derive_pubkey_from_signer(self.signer_file)

    def persist(self):
        data: Dict[str, Any] = {
            "sol_rpc":         self.rpc_http,
            "store_program_id":self.store_pid,
            "signer_file":     str(self.signer_file),
            "signer_pubkey":   self.signer_pubkey or "",
            "owner_offset":    self.owner_offset,
            "limit":           self.limit,
            "page":            self.page,
        }
        save_json(data, DEFAULT_JSON)

    def rpc(self) -> SolanaRpcClient:
        return SolanaRpcClient(self.rpc_http)

    def header(self):
        print("="*72)
        print(" GMX-Solana Interactive Console (Option A) ".center(72, " "))
        print("="*72)
        print(f" RPC        : {self.rpc_http or '(not set)'}")
        print(f" Store PID  : {self.store_pid or '(not set)'}")
        print(f" Signer File: {self.signer_file}")
        print(f" Signer Pub : {self.signer_pubkey or '(not derived)'}")
        print(f" OwnerOff   : {self.owner_offset}   Paging: limit={self.limit} page={self.page}")
        print(f" Config JSON: {DEFAULT_JSON}")
        print("-"*72)

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
        print("  [8] Sweep offsets (quick)")
        print("  [9] Show first match (raw)")
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
                pid = input(f"Store Program ID [{sess.store_pid}]: ").strip()
                if pid:
                    sess.store_pid = pid
                    sess.persist()
                input("\n<enter>")

            elif choice == "3":
                p = input(f"Signer file path [{sess.signer_file}]: ").strip()
                if p:
                    sess.signer_file = Path(p)
                pub = derive_pubkey_from_signer(sess.signer_file)
                if pub:
                    sess.signer_pubkey = pub
                    print("Derived signer pubkey:", pub)
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
                elif not sess.signer_pubkey:
                    print("⚠️  Derive signer pubkey in menu [3].")
                else:
                    try:
                        n, sample = memcmp_count(
                            rpc_url=sess.rpc_http,
                            program_id=sess.store_pid,
                            wallet_b58=sess.signer_pubkey,
                            owner_offset=sess.owner_offset,
                            limit=max(1, sess.limit),
                            page=max(1, sess.page),
                        )
                        print(pretty({"matched_account_count": n, "sample_pubkeys": sample}))
                    except Exception as e:
                        print("error:", e)
                input("\n<enter>")

            elif choice == "6":
                if not sess.store_pid:
                    print("⚠️  Set Store Program ID first (menu [2]).")
                else:
                    pub = input(f"Wallet pubkey [{sess.signer_pubkey or ''}]: ").strip() or (sess.signer_pubkey or "")
                    if not pub:
                        print("no pubkey entered.")
                    else:
                        try:
                            ensure_base58(pub, "Wallet pubkey")
                            n, sample = memcmp_count(
                                rpc_url=sess.rpc_http,
                                program_id=sess.store_pid,
                                wallet_b58=pub,
                                owner_offset=sess.owner_offset,
                                limit=max(1, sess.limit),
                                page=max(1, sess.page),
                            )
                            print(pretty({"matched_account_count": n, "sample_pubkeys": sample}))
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

            elif choice == "8":
                if not sess.store_pid or not sess.signer_pubkey:
                    print("⚠️  Set Store PID [2] and Signer [3] first.")
                else:
                    offsets = [0,8,16,24,32,40,48,56,64,72,80,96,112,128]
                    sweep = memcmp_sweep(sess.rpc_http, sess.store_pid, sess.signer_pubkey, offsets=offsets, limit=max(1, sess.limit))
                    print(pretty({"sweep": sweep}))
                input("\n<enter>")

            elif choice == "9":
                if not sess.store_pid or not sess.signer_pubkey:
                    print("⚠️  Set Store PID [2] and Signer [3] first.")
                else:
                    n, sample = memcmp_count(sess.rpc_http, sess.store_pid, sess.signer_pubkey, owner_offset=sess.owner_offset, limit=max(1, sess.limit), page=max(1, sess.page))
                    if n <= 0 or not sample:
                        print("No matches on this page.")
                    else:
                        first = sample[0]
                        print("first match pubkey:", first)
                        val = fetch_account_base64(sess.rpc_http, first)
                        # Print short peek so console isn't flooded
                        v = val.get("value") or {}
                        d = v.get("data")
                        peek = d[0][:160] + "..." if isinstance(d, list) and d else "(no data)"
                        print(pretty({"owner": v.get("owner"), "space": v.get("space"), "lamports": v.get("lamports"), "data_peek": peek}))
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
        print("⚠️  No RPC endpoint configured. Set sol_rpc in C:\\sonic7\\gmx_solana_console.json and restart.")
        return 2
    menu_loop(sess)
    return 0

if __name__ == "__main__":
    sys.exit(main())
