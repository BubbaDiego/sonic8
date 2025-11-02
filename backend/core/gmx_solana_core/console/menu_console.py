"""
GMX-Solana Interactive Console (Option A hardened)
- JSON config only; no envs. Default: C:\sonic7\gmx_solana_console.json
- Shows signer pubkey in header (derived or json override)
- Positions via memcmp:
    * Helius V2 cursor-based by default (reliable)
    * V1 fallback for non-Helius RPCs
    * Optional dataSize filter
- Extras:
    [8] Sweep offsets (diagnostic)
    [9] Show first match (raw peek)
   [10] Toggle V2 preference (on Helius)
   [11] Set dataSize filter
"""

from __future__ import annotations
import os
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..clients.solana_rpc_client import SolanaRpcClient, RpcError
from ..services.market_service import MarketService  # unchanged
from ..config_loader import load_solana_config, pretty  # pretty() exists in your tree
from .config_io import load_json, save_json, DEFAULT_JSON
from ..services.memcmp_service import (
    memcmp_find,
    memcmp_sweep_v2,
    memcmp_count_v1,
    fetch_account_base64,
)

DEFAULT_CFG = Path(__file__).resolve().parent.parent / "config" / "solana.yaml"


def _is_base58(s: str) -> bool:
    return isinstance(s, str) and len(s) >= 32 and re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]+", s or "") is not None


def _derive_pub_from_signer(signer_path: Path) -> Optional[str]:
    """
    Prefer base58 pubkey anywhere in the file; else tolerant BIP-39 (12/15/18/21/24).
    No third-party deps required for base58 path.
    """
    if not signer_path.exists():
        return None

    txt = signer_path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"[1-9A-HJ-NP-Za-km-z]{32,}", txt)
    if m:
        return m.group(0)

    # Optional BIP-39: if bip_utils available in venv, use it
    try:
        from bip_utils import (
            Bip39MnemonicValidator,
            Bip39SeedGenerator,
            Bip44,
            Bip44Coins,
            Bip44Changes,
        )
    except Exception:
        return None

    clean = re.sub(r"[^A-Za-z\s]", " ", txt).lower()
    words = [w for w in clean.split() if w]
    for n in (24, 21, 18, 15, 12):
        if len(words) >= n:
            cand = " ".join(words[:n])
            try:
                Bip39MnemonicValidator(cand).Validate()
                seed = Bip39SeedGenerator(cand).Generate()
                ctx = Bip44.FromSeed(seed, Bip44Coins.SOLANA)
                acct = (
                    ctx.Purpose()
                    .Coin()
                    .Account(0)
                    .Change(Bip44Changes.CHAIN_EXT)
                    .AddressIndex(0)
                )
                return acct.PublicKey().ToAddress()
            except Exception:
                continue
    return None


def _is_helius(rpc: str) -> bool:
    return "helius-rpc.com" in (rpc or "").lower()


class Session:
    def __init__(self):
        j = load_json(DEFAULT_JSON)
        try:
            y = load_solana_config(str(DEFAULT_CFG))
        except Exception:
            y = {}

        self.rpc_http: str = j.get("sol_rpc") or y.get("rpc_http") or ""
        self.store_pid: str = (
            j.get("store_program_id")
            or (y.get("programs") or {}).get("store")
            or ""
        )
        self.signer_file: Path = Path(j.get("signer_file") or r"C:\sonic7\signer.txt")
        if not self.signer_file.exists():
            # fallback probes
            for p in [
                Path.cwd() / "signer.txt",
                Path.cwd() / "signer",
                Path(r"C:\sonic7\signer"),
            ]:
                if p.exists():
                    self.signer_file = p
                    break

        self.signer_pubkey: Optional[str] = j.get("signer_pubkey") or _derive_pub_from_signer(self.signer_file)

        # paging/config knobs
        self.limit: int = int(j.get("limit") or 100)
        self.page: int = int(j.get("page") or 1)
        self.owner_offset: int = int(j.get("owner_offset") or 24)  # your sweep showed 24 hits
        self.data_size: Optional[int] = (
            int(j["data_size"]) if ("data_size" in j and str(j["data_size"]).isdigit()) else None
        )
        self.prefer_v2: bool = bool(j.get("prefer_v2", True))  # use V2 if on Helius

    def persist(self) -> None:
        out: Dict[str, Any] = {
            "sol_rpc": self.rpc_http,
            "store_program_id": self.store_pid,
            "signer_file": str(self.signer_file),
            "signer_pubkey": self.signer_pubkey or "",
            "limit": self.limit,
            "page": self.page,
            "owner_offset": self.owner_offset,
            "data_size": self.data_size if self.data_size else 0,
            "prefer_v2": self.prefer_v2,
        }
        save_json(out, DEFAULT_JSON)

    def rpc(self) -> SolanaRpcClient:
        return SolanaRpcClient(self.rpc_http)

    def header(self) -> None:
        print("=" * 72)
        print(" GMX-Solana Interactive Console (Option A: hardened) ".center(72, " "))
        print("=" * 72)
        print(f" RPC        : {self.rpc_http or '(not set)'}")
        print(f" Store PID  : {self.store_pid or '(not set)'}")
        print(f" Signer File: {self.signer_file}")
        print(f" Signer Pub : {self.signer_pubkey or '(not derived)'}")
        ds = self.data_size if self.data_size else "(none)"
        v2 = "on" if (self.prefer_v2 and _is_helius(self.rpc_http)) else "off"
        print(f" OwnerOff   : {self.owner_offset}   Paging: limit={self.limit} page={self.page}")
        print(f" Filters    : dataSize={ds}  V2={v2}")
        print(f" Config JSON: {DEFAULT_JSON}")
        print("-" * 72)


def _wait() -> None:
    input("\n<enter>")


def menu_loop(sess: Session) -> None:
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
        print(" [10] Toggle V2 preference (Helius)")
        print(" [11] Set/clear dataSize filter")
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
                _wait()

            elif choice == "2":
                pid = input(f"Store Program ID [{sess.store_pid}]: ").strip()
                if pid:
                    sess.store_pid = pid
                    sess.persist()
                _wait()

            elif choice == "3":
                p = input(f"Signer file path [{sess.signer_file}]: ").strip()
                if p:
                    sess.signer_file = Path(p)
                pub = _derive_pub_from_signer(sess.signer_file)
                if pub:
                    sess.signer_pubkey = pub
                    print("Derived signer pubkey:", pub)
                else:
                    print("⚠️  Could not derive signer pubkey from file.")
                sess.persist()
                _wait()

            elif choice == "4":
                if not sess.store_pid:
                    print("⚠️  Set Store Program ID first (menu [2]).")
                else:
                    try:
                        ms = MarketService(sess.rpc())
                        out = ms.list_markets_basic(sess.store_pid, limit=sess.limit, page=sess.page)
                        print(pretty(out))
                    except Exception as e:
                        print("error:", e)
                _wait()

            elif choice == "5":
                if not sess.store_pid:
                    print("⚠️  Set Store Program ID first (menu [2]).")
                elif not sess.signer_pubkey:
                    print("⚠️  Derive or set signer pubkey (menu [3]).")
                else:
                    try:
                        n, sample, mode = memcmp_find(
                            rpc_url=sess.rpc_http,
                            program_id=sess.store_pid,
                            wallet_b58=sess.signer_pubkey,
                            owner_offset=sess.owner_offset,
                            limit=sess.limit,
                            page=sess.page,
                            data_size=sess.data_size,
                            prefer_v2=sess.prefer_v2,
                        )
                        print(pretty({"mode": mode, "matched_account_count": n, "sample_pubkeys": sample}))
                    except Exception as e:
                        print("error:", e)
                _wait()

            elif choice == "6":
                if not sess.store_pid:
                    print("⚠️  Set Store Program ID first (menu [2]).")
                else:
                    pub = input(f"Wallet pubkey [{sess.signer_pubkey or ''}]: ").strip() or (sess.signer_pubkey or "")
                    if not pub or not _is_base58(pub):
                        print("Invalid or empty base58 pubkey.")
                    else:
                        try:
                            n, sample, mode = memcmp_find(
                                rpc_url=sess.rpc_http,
                                program_id=sess.store_pid,
                                wallet_b58=pub,
                                owner_offset=sess.owner_offset,
                                limit=sess.limit,
                                page=sess.page,
                                data_size=sess.data_size,
                                prefer_v2=sess.prefer_v2,
                            )
                            print(pretty({"mode": mode, "matched_account_count": n, "sample_pubkeys": sample}))
                        except Exception as e:
                            print("error:", e)
                _wait()

            elif choice == "7":
                try:
                    sess.limit = int(input(f"limit [{sess.limit}]: ").strip() or sess.limit)
                    sess.page = int(input(f"page  [{sess.page }]: ").strip() or sess.page)
                    sess.owner_offset = int(input(f"owner offset [{sess.owner_offset}]: ").strip() or sess.owner_offset)
                    sess.persist()
                except Exception as e:
                    print("bad input:", e)
                _wait()

            elif choice == "8":
                if not sess.store_pid or not sess.signer_pubkey:
                    print("⚠️  Set Store PID [2] and Signer [3] first.")
                else:
                    offsets = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 96, 112, 128]
                    if _is_helius(sess.rpc_http) and sess.prefer_v2:
                        sweep = memcmp_sweep_v2(
                            rpc_url=sess.rpc_http,
                            program_id=sess.store_pid,
                            wallet_b58=sess.signer_pubkey,
                            offsets=offsets,
                            limit=max(1, sess.limit),
                            data_size=sess.data_size,
                        )
                        print(pretty({"mode": "v2", "sweep": sweep}))
                    else:
                        # Fallback quick sweep using V1 (first page only)
                        out = []
                        for off in offsets:
                            try:
                                n, _ = memcmp_count_v1(
                                    rpc_url=sess.rpc_http,
                                    program_id=sess.store_pid,
                                    wallet_b58=sess.signer_pubkey,
                                    owner_offset=off,
                                    limit=max(1, sess.limit),
                                    page=1,
                                    data_size=sess.data_size,
                                )
                                out.append((off, n))
                            except Exception:
                                out.append((off, -1))
                        print(pretty({"mode": "v1", "sweep": out}))
                _wait()

            elif choice == "9":
                if not sess.store_pid or not sess.signer_pubkey:
                    print("⚠️  Set Store PID [2] and Signer [3] first.")
                else:
                    try:
                        n, sample, mode = memcmp_find(
                            rpc_url=sess.rpc_http,
                            program_id=sess.store_pid,
                            wallet_b58=sess.signer_pubkey,
                            owner_offset=sess.owner_offset,
                            limit=sess.limit,
                            page=sess.page,
                            data_size=sess.data_size,
                            prefer_v2=sess.prefer_v2,
                        )
                        if n <= 0 or not sample:
                            print("No matches.")
                        else:
                            first = sample[0]
                            print("first match pubkey:", first)
                            val = fetch_account_base64(sess.rpc_http, first)
                            v = (val or {}).get("value") or {}
                            lamports = v.get("lamports")
                            space = v.get("space")
                            data = v.get("data")
                            if isinstance(data, list) and data:
                                peek = data[0][:160] + "..."
                            else:
                                peek = "(no data)"
                            print(pretty({"mode": mode, "lamports": lamports, "space": space, "data_peek": peek}))
                    except Exception as e:
                        print("error:", e)
                _wait()

            elif choice == "10":
                sess.prefer_v2 = not bool(sess.prefer_v2)
                print("prefer_v2 =", sess.prefer_v2)
                sess.persist()
                _wait()

            elif choice == "11":
                cur = sess.data_size if sess.data_size else 0
                raw = input(f"dataSize (0 to clear) [{cur}]: ").strip()
                try:
                    val = int(raw) if raw else cur
                    sess.data_size = val if val > 0 else None
                    sess.persist()
                except Exception as e:
                    print("bad input:", e)
                _wait()

            elif choice == "0":
                print("Bye.")
                return

        except KeyboardInterrupt:
            print("\nBye.")
            return
        except Exception as e:
            print("Unhandled error:", e)
            _wait()


def main() -> int:
    sess = Session()
    if not sess.rpc_http:
        print("⚠️  No RPC endpoint configured. Set sol_rpc in", DEFAULT_JSON)
        return 2
    menu_loop(sess)
    return 0


if __name__ == "__main__":
    sys.exit(main())
