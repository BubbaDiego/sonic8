r"""
GMX-Solana Interactive Console (Option A: hardened + builders)
- JSON config only; default: C:\\sonic7\\gmx_solana_console.json
- Shows signer pubkey in header (derived or json override)
- Positions via memcmp (Helius GPA-v2 / v1 fallback), optional dataSize filter

NEW (spec-aligned, IDL-driven):
  ✳ prepare_position           → manifest
  💰 create_deposit            → manifest
  💸 create_withdrawal         → manifest
  🧾 create_order_v2           → manifest
Manifests saved to: C:\\sonic7\\outbox\\YYYYMMDD_HHMMSS_<action>.json
"""

from __future__ import annotations
import os
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..clients.solana_rpc_client import SolanaRpcClient, RpcError
from ..services.market_service import MarketService
from ..config_loader import load_solana_config, pretty
from .config_io import load_json, save_json, DEFAULT_JSON
from ..services.memcmp_service import (
    memcmp_find,
    memcmp_sweep_v2,
    memcmp_count_v1,
    fetch_account_base64,
)

# NEW: IDL + builders + outbox
from ..actions.idl_loader import load_idl, DEFAULT_IDL_PATH
from ..actions.builders import build_manifest
from ..actions.outbox import write_manifest, DEFAULT_OUTBOX

DEFAULT_CFG = Path(__file__).resolve().parent.parent / "config" / "solana.yaml"


# ---------- helpers ----------
def _is_base58(s: str) -> bool:
    return isinstance(s, str) and len(s) >= 32 and re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]+", s or "") is not None


def _is_helius(rpc: str) -> bool:
    return "helius-rpc.com" in (rpc or "").lower()


def _derive_pub_from_signer(signer_path: Path) -> Optional[str]:
    """Prefer base58 in file; else tolerant BIP-39 if bip_utils present."""
    if not signer_path.exists():
        return None
    txt = signer_path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"[1-9A-HJ-NP-Za-km-z]{32,}", txt)
    if m:
        return m.group(0)
    try:
        from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
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
                acct = ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                return acct.PublicKey().ToAddress()
            except Exception:
                continue
    return None


def _summary_banner(title: str) -> None:
    print("\n" + "─" * 72)
    print(f" {title} ".center(72, "─"))
    print("─" * 72)


def _warn_offset8() -> None:
    print("ℹ️  Hint: your last sweep showed hits at offset 24/56. Use [12] to auto-apply best offset.")


# ---------- console session ----------
class Session:
    def __init__(self):
        j = load_json(DEFAULT_JSON)
        try:
            y = load_solana_config(str(DEFAULT_CFG))
        except Exception:
            y = {}

        self.rpc_http: str = j.get("sol_rpc") or y.get("rpc_http") or ""
        # NOTE: this is the PROGRAM ID (Store program), not a data account
        self.store_pid: str = j.get("store_program_id") or (y.get("programs") or {}).get("store") or ""
        self.signer_file: Path = Path(j.get("signer_file") or r"C:\\sonic7\\signer.txt")
        if not self.signer_file.exists():
            for p in [Path.cwd()/"signer.txt", Path.cwd()/"signer", Path(r"C:\\sonic7\\signer")]:
                if p.exists():
                    self.signer_file = p
                    break

        self.signer_pubkey: Optional[str] = j.get("signer_pubkey") or _derive_pub_from_signer(self.signer_file)
        self.limit: int = int(j.get("limit") or 100)
        self.page: int = int(j.get("page") or 1)
        self.owner_offset: int = int(j.get("owner_offset") or 24)
        self.data_size: Optional[int] = (
            int(j["data_size"]) if ("data_size" in j and str(j["data_size"]).isdigit()) else None
        )
        self.prefer_v2: bool = bool(j.get("prefer_v2", True))

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
        print("      🌊 GMX‑Solana Interactive Console (Option A + builders)      ".center(72, " "))
        print("=" * 72)
        print(f" 🚀 RPC        : {self.rpc_http or '(not set)'}")
        print(f" 🏦 Store PID  : {self.store_pid or '(not set)'}")
        print(f" 📝 Signer File: {self.signer_file}")
        print(f" 👤 Signer Pub : {self.signer_pubkey or '(not derived)'}")
        ds = self.data_size if self.data_size else "(none)"
        v2 = "on" if (self.prefer_v2 and _is_helius(self.rpc_http)) else "off"
        print(f" 🧭 OwnerOff   : {self.owner_offset}   📦 limit={self.limit}  🧺 page={self.page}")
        print(f" 🔎 Filters    : dataSize={ds}  V2={v2}")
        print(f" ⚙️  Config JSON: {DEFAULT_JSON}")
        print(f" 📂 Outbox     : {DEFAULT_OUTBOX}")
        print("-" * 72)


def _wait() -> None:
    input("\n<enter>")


# ---------- IDL helper ----------
def _need_idl(sess: Session) -> Optional[Dict[str, Any]]:
    idl = load_idl(program_id=sess.store_pid, rpc_url=sess.rpc_http)
    # determine the resolved path for user messaging
    from ..actions.idl_loader import _json_idl_path_override, DEFAULT_IDL_PATH
    resolved = _json_idl_path_override() or DEFAULT_IDL_PATH
    if not idl:
        print("⚠️  IDL not found. Save it at:")
        print("    ", resolved)
        print("    Anchor CLI (if installed):")
        print(f"      anchor idl fetch -o {resolved} {sess.store_pid}")
        print("    Or copy the official gmsol-store IDL JSON into that path.")
    return idl


def _build_and_write(sess: Session, ix_name: str, action_tag: str) -> None:
    if not sess.store_pid:
        print("⚠️  Set Store Program ID first (menu [2])."); _wait(); return
    if not sess.signer_pubkey:
        print("⚠️  Derive or set signer pubkey (menu [3])."); _wait(); return

    idl = _need_idl(sess)
    if not idl:
        _wait()
        return

    mf = build_manifest(
        action_name=action_tag,
        ix_name=ix_name,
        program_id=sess.store_pid,
        rpc_url=sess.rpc_http,
        signer=sess.signer_pubkey,
        idl=idl,
        extra_meta={"note": "Fill any blank account pubkey and arg 'value' fields before encoding/sending."}
    )
    path = write_manifest(mf, suggested_name=action_tag)
    missing = mf["meta"].get("missing_accounts") or []
    filled = [a for a in mf["accounts"] if a.get("pubkey")]
    blanks = [a for a in mf["accounts"] if not a.get("pubkey")]
    print("✅ Manifest created:", path)
    print("• 🧾 Instruction :", mf["instruction"])
    print(f"• 🧩 Accounts    : {len(mf['accounts'])} total → {len(filled)} filled, {len(blanks)} pending")
    if missing:
        print("• ❗ Missing     :", ", ".join(missing))
    print("• 🧷 Args        :", ", ".join([a['name'] for a in (mf['args'] or [])]) or "(none)")
    print("• 🔑 Discriminator (hex):", mf["anchorDiscriminatorHex"])
    print("• 📂 Outbox      :", DEFAULT_OUTBOX)
    _wait()


# ---------- main loop ----------
def menu_loop(sess: Session) -> None:
    while True:
        sess.header()
        print("  [1]  🩺 RPC health")
        print("  [2]  🏦 Set Store Program ID")
        print("  [3]  ✍️  Set Signer file path (re-derive pubkey)")
        print("  [4]  🧮 Markets (paged)")
        print("  [5]  📌 Positions (from signer)")
        print("  [6]  🔍 Positions (enter pubkey)")
        print("  [7]  🧭 Set paging (limit/page/owner-offset)")
        print("  [8]  🧪 Sweep offsets (quick)")
        print("  [9]  🧬 Show first match (raw)")
        print(" [10]  🔁 Toggle V2 preference (Helius)")
        print(" [11]  🔧 Set/clear dataSize filter")
        print(" [12]  🧠 Auto-apply best offset from sweep")
        print(" ───────────────────────────────────────────────────────────────")
        print(" [20]  ✳ Prepare Position  → manifest (prepare_position)")
        print(" [21]  💰 Create Deposit    → manifest (create_deposit)")
        print(" [22]  💸 Create Withdrawal → manifest (create_withdrawal)")
        print(" [23]  🧾 Create Order      → manifest (create_order_v2)")
        print(" [24]  📂 Show outbox path")
        print("  [0]  🚪 Exit")
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
                        n, sample, mode, dbg = memcmp_find(
                            rpc_url=sess.rpc_http,
                            program_id=sess.store_pid,
                            wallet_b58=sess.signer_pubkey,
                            owner_offset=sess.owner_offset,
                            limit=sess.limit,
                            page=sess.page,
                            data_size=sess.data_size,
                            prefer_v2=sess.prefer_v2,
                        )
                        print(pretty({
                            "mode": mode,
                            "matched_account_count": n,
                            "sample_pubkeys": sample,
                            "effective_filters": dbg.get("filters"),
                            "pages": dbg.get("pages"),
                            "paginationKey": dbg.get("final_paginationKey", "(n/a)")
                        }))
                        _summary_banner("Summary")
                        # quick emoji summary
                        scanned = sum(p.get("returned", 0) for p in (dbg.get("pages") or []) if isinstance(p, dict))
                        print(f" ✅ Matches: {n}   📌 First: {(sample or ['(none)'])[0]}   📄 Returned: {scanned}")
                        print(f" 🔎 Filters: owner_offset={sess.owner_offset}, dataSize={sess.data_size or '(none)'}")
                        if sess.owner_offset == 8:
                            _warn_offset8()
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
                            n, sample, mode, dbg = memcmp_find(
                                rpc_url=sess.rpc_http,
                                program_id=sess.store_pid,
                                wallet_b58=pub,
                                owner_offset=sess.owner_offset,
                                limit=sess.limit,
                                page=sess.page,
                                data_size=sess.data_size,
                                prefer_v2=sess.prefer_v2,
                            )
                            print(pretty({
                                "mode": mode,
                                "matched_account_count": n,
                                "sample_pubkeys": sample,
                                "effective_filters": dbg.get("filters"),
                                "pages": dbg.get("pages"),
                                "paginationKey": dbg.get("final_paginationKey", "(n/a)")
                            }))
                            _summary_banner("Summary")
                            scanned = sum(p.get("returned", 0) for p in (dbg.get("pages") or []) if isinstance(p, dict))
                            print(f" ✅ Matches: {n}   📌 First: {(sample or ['(none)'])[0]}   📄 Returned: {scanned}")
                            print(f" 🔎 Filters: owner_offset={sess.owner_offset}, dataSize={sess.data_size or '(none)'}")
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
                        n, sample, mode, dbg = memcmp_find(
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
                            print(pretty({
                                "mode": mode,
                                "matched_account_count": n,
                                "sample_pubkeys": sample,
                                "effective_filters": dbg.get("filters"),
                                "pages": dbg.get("pages"),
                                "paginationKey": dbg.get("final_paginationKey", "(n/a)")
                            }))
                            _summary_banner("Summary")
                            scanned = sum(p.get("returned", 0) for p in (dbg.get("pages") or []) if isinstance(p, dict))
                            print(f" ⚠️ No matches.  📄 Returned: {scanned}")
                        else:
                            first = sample[0]
                            print("first match pubkey:", first)
                            val = fetch_account_base64(sess.rpc_http, first)
                            v = (val or {}).get("value") or {}
                            lamports = v.get("lamports")
                            space = v.get("space")
                            data = v.get("data")
                            peek = data[0][:160] + "..." if (isinstance(data, list) and data) else "(no data)"
                            print(pretty({
                                "mode": mode,
                                "matched_account_count": n,
                                "first_pubkey": first,
                                "owner": v.get("owner"),
                                "space": space,
                                "lamports": lamports,
                                "paginationKey": dbg.get("final_paginationKey", "(n/a)"),
                            }))
                            _summary_banner("Summary")
                            print(f" ✅ First: {first}   📦 Space: {space}   💎 Lamports: {lamports}")
                            print(f" 🔬 Peek: {peek}")
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

            elif choice == "12":
                if not sess.store_pid or not sess.signer_pubkey:
                    print("⚠️  Set Store PID [2] and Signer [3] first.")
                else:
                    candidates = [0, 8, 16, 24, 32, 40, 48, 56, 64]
                    if _is_helius(sess.rpc_http) and sess.prefer_v2:
                        sweep = memcmp_sweep_v2(
                            rpc_url=sess.rpc_http,
                            program_id=sess.store_pid,
                            wallet_b58=sess.signer_pubkey,
                            offsets=candidates,
                            limit=max(1, sess.limit),
                            data_size=sess.data_size,
                        )
                        print(pretty({"auto_sweep_v2": sweep}))
                        best_off = max(sweep, key=lambda t: t[1])[0] if sweep else sess.owner_offset
                    else:
                        best_off, best_cnt = sess.owner_offset, -1
                        for off in candidates:
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
                                if n > best_cnt:
                                    best_cnt = n
                                    best_off = off
                            except Exception:
                                continue
                        print(pretty({"auto_sweep_v1": [[best_off, best_cnt]]}))
                    print("Applying owner_offset =", best_off)
                    sess.owner_offset = best_off
                    sess.persist()
                _wait()

            # ── NEW: builders (IDL-driven, manifest outbox) ───────────────
            elif choice == "20":
                _build_and_write(sess, "prepare_position", "prepare_position")

            elif choice == "21":
                _build_and_write(sess, "create_deposit", "create_deposit")

            elif choice == "22":
                _build_and_write(sess, "create_withdrawal", "create_withdrawal")

            elif choice == "23":
                _build_and_write(sess, "create_order_v2", "create_order_v2")

            elif choice == "24":
                print("📂 Outbox:", DEFAULT_OUTBOX)
                try:
                    if os.name == "nt":
                        os.startfile(str(DEFAULT_OUTBOX))
                except Exception:
                    pass
                _wait()

            elif choice == "0":
                print("Bye. ✌️")
                return

        except KeyboardInterrupt:
            print("\nBye. ✌️")
            return
        except Exception as e:
            print("Unhandled error:", e)
            _wait()


def main() -> int:
    sess = Session()
    if not sess.rpc_http:
        print("⚠️  No RPC endpoint configured. Set sol_rpc in", DEFAULT_JSON)
        return 2
    if sess.owner_offset == 8:
        print("ℹ️  Hint: your last sweep showed hits at offset 24/56. Use [12] to auto-apply best offset.")
    menu_loop(sess)
    return 0


if __name__ == "__main__":
    sys.exit(main())
