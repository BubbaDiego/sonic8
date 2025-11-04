# -*- coding: utf-8 -*-
"""
GMX-Solana Interactive Console
Drop-in replacement that expects a JSON config file at project root:
  C:\sonic7\gmx_solana_console.json

Features:
 - JSON config only (no env reliance)
 - signer pubkey derivation (bip-utils optional)
 - Helius-friendly GPA-v2 usage with paging
 - offset sweep, auto-apply best offset
 - builder manifests written to outbox/
 - debug logging + friendly summaries + unicode icons
"""
from __future__ import annotations
import os
import sys
import json
import re
import time
import base64
import hashlib
import pathlib
from datetime import datetime
from urllib.request import Request, urlopen
from typing import Optional, Dict, Any, List, Tuple

ROOT = pathlib.Path.cwd()
CONFIG_PATH = ROOT / "gmx_solana_console.json"
OUTBOX_DIR = ROOT / "outbox"
IDL_PATH = ROOT / "backend" / "core" / "gmx_solana_core" / "idl" / "gmsol-store.json"

TOKEN_PROGRAM_2022 = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
TOKEN_PROGRAM_CLASSIC = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
SPL_TOKEN = TOKEN_PROGRAM_CLASSIC

# ensure outbox exists
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

# try bip-utils for mnemonic -> pubkey if available
try:
    from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
    _BIP_OK = True
except Exception:
    _BIP_OK = False

# ========= Helpers =========
def load_config(path: pathlib.Path = CONFIG_PATH) -> Dict[str, Any]:
    if not path.exists():
        # default minimal config
        default = {
            "sol_rpc": os.getenv("SOL_RPC", ""),
            "store_program_id": "",
            "signer_file": str(ROOT / "signer.txt"),
            "owner_offset": 8,
            "limit": 100,
            "page": 1
        }
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def rpc_call(rpc_url: str, method: str, params: list, timeout: int = 20) -> Any:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = Request(rpc_url, data=body, headers={"Content-Type": "application/json", "User-Agent": "gmx-solana-console"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode()
        data = json.loads(raw)
    if "error" in data:
        raise RuntimeError(data["error"])
    return data.get("result")

def derive_pub_from_signer_file(path: str) -> Optional[str]:
    """Try bip-utils derivation (24/21/18/15/12), else fallback to first base58 token."""
    p = pathlib.Path(path)
    if not p.exists():
        return None
    txt = p.read_text(encoding="utf-8", errors="ignore").strip()
    # try bip-utils if available
    if _BIP_OK:
        words_clean = re.sub(r"[^A-Za-z\s]", " ", txt).lower().split()
        for n in (24, 21, 18, 15, 12):
            if len(words_clean) >= n:
                cand = " ".join(words_clean[:n])
                try:
                    Bip39MnemonicValidator(cand).Validate()
                    seed = Bip39SeedGenerator(cand).Generate()
                    ctx = Bip44.FromSeed(seed, Bip44Coins.SOLANA)
                    acct = ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                    return acct.PublicKey().ToAddress()
                except Exception:
                    continue
    # fallback: search for base58-like token
    m = re.search(r"[1-9A-HJ-NP-Za-km-z]{32,}", txt)
    return m.group(0) if m else None

def compute_anchor_discriminator(name: str) -> str:
    """Anchor discriminator: first 8 bytes of sha256(b'global:<name>') returned as hex string."""
    h = hashlib.sha256(f"global:{name}".encode()).digest()
    return h[:8].hex()

def pretty_summary_raw_accounts(sample_pubkeys: List[str], matched_count: int, offsets: List[Tuple[int, int]], rpc_url: str) -> Dict[str, Any]:
    # human friendly short summary
    summary = {
        "matched_account_count": matched_count,
        "sample_count": len(sample_pubkeys),
        "sample_pubkeys": sample_pubkeys[:10],
        "offset_sweep": offsets,
        "rpc": rpc_url
    }
    # add friendly markers
    return summary


def _acc_shape_is_dict(man: dict) -> bool:
    return isinstance(man.get("accounts"), dict)


def _acc_get(man: dict, key: str) -> Optional[str]:
    acc = man.get("accounts")
    if isinstance(acc, dict):
        return acc.get(key)
    if isinstance(acc, list):
        for item in acc:
            if isinstance(item, dict) and item.get("name") == key:
                return item.get("pubkey") or ""
    return None


def _acc_set(man: dict, key: str, value: str) -> None:
    if not value:
        return
    acc = man.get("accounts")
    if isinstance(acc, dict):
        acc[key] = value
        return
    if isinstance(acc, list):
        for item in acc:
            if isinstance(item, dict) and item.get("name") == key:
                item["pubkey"] = value
                return
        acc.append({"name": key, "pubkey": value, "isMut": False, "isSigner": False})


def write_manifest(
    instruction_name: str,
    idl: Dict[str, Any],
    outdir: pathlib.Path = OUTBOX_DIR,
    prefill_accounts: Optional[Dict[str, str]] = None,
) -> Tuple[pathlib.Path, Dict[str, Any]]:
    outdir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fname = f"{timestamp}_{instruction_name}.json"
    fp = outdir / fname
    # build manifest using IDL if present (accounts/args). Fallback to stub.
    manifest = {
        "instruction": instruction_name,
        "accounts": [],
        "args": [],
        "discriminator": None
    }
    if idl and isinstance(idl, dict):
        # find instruction entry
        ins = next((i for i in idl.get("instructions", []) if i.get("name") == instruction_name), None)
        if ins:
            manifest["accounts"] = ins.get("accounts", [])
            manifest["args"] = ins.get("args", [])
    # compute discriminator anyway
    manifest["discriminator"] = compute_anchor_discriminator(instruction_name)
    if prefill_accounts:
        for key, value in prefill_accounts.items():
            if not _acc_get(manifest, key):
                _acc_set(manifest, key, value)
    fp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return fp, manifest

# ========= IDL load =========
def load_idl(path: pathlib.Path = IDL_PATH) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

# ========= RPC helpers for GMX store queries =========
def gpa_v2_get_program_accounts(rpc: str, program_id: str, limit: int = 100, page: int = 1, filters: dict = None) -> List[dict]:
    """Use getProgramAccountsV2 pagination-friendly call (Helius-ish)."""
    cfg = {"encoding": "base64", "commitment": "confirmed", "limit": limit, "page": page}
    if filters:
        cfg.update(filters)
    res = rpc_call(rpc, "getProgramAccounts", [program_id, cfg])
    # some RPCs (Helius) return list; others return dict — normalize
    if isinstance(res, dict) and "result" in res:
        return res["result"]
    return res if isinstance(res, list) else []

def memcmp_probe_count(rpc: str, program_id: str, owner_pubkey: str, offset: int, page_limit: int = 100) -> int:
    try:
        cfg = {"encoding": "base64", "commitment": "confirmed", "limit": page_limit, "page": 1,
               "filters": [{"memcmp": {"offset": offset, "bytes": owner_pubkey}}]}
        res = rpc_call(rpc, "getProgramAccounts", [program_id, cfg])
        return len(res) if isinstance(res, list) else 0
    except Exception:
        return 0

# ========= Console UI =========
ICONS = {
    "rpc": "🩺",
    "store": "🏦",
    "signer": "📝",
    "owner": "👤",
    "page": "🧭",
    "filters": "🔎",
    "cfg": "⚙️",
    "outbox": "📂",
    "ok": "✅",
    "warn": "⚠️",
    "exit": "🚪",
    "make": "🧾",
}

def clear():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

def print_header(cfg: Dict[str, Any], signer_pub: Optional[str], idl_present: bool, data_size_filter: Optional[int], v2_pref: bool):
    clear()
    print("=" * 72)
    print("         🌊 GMX-Solana Interactive Console (Option A + builders)")
    print("=" * 72)
    print(f" {ICONS['rpc']} RPC        : {cfg.get('sol_rpc') or '(not set)'}")
    print(f" {ICONS['store']} Store PID  : {cfg.get('store_program_id') or '(not set)'}")
    print(f" {ICONS['signer']} Signer File: {cfg.get('signer_file')}")
    print(f" {ICONS['owner']} Signer Pub : {signer_pub or '(not derived)'}")
    print(f" {ICONS['page']} OwnerOff   : {cfg.get('owner_offset', 8)}   📦 limit={cfg.get('limit',100)}  🧺 page={cfg.get('page',1)}")
    ds = "(none)" if data_size_filter is None else str(data_size_filter)
    v2s = "on" if v2_pref else "off"
    print(f" {ICONS['filters']} Filters    : dataSize={ds}  V2={v2s}")
    print(f" {ICONS['cfg']} Config JSON: {CONFIG_PATH}")
    print(f" {ICONS['outbox']} Outbox     : {OUTBOX_DIR}")
    print("-" * 72)

def interactive_menu():
    cfg = load_config()
    idl = load_idl()
    signer_file = cfg.get("signer_file", str(ROOT / "signer.txt"))
    signer_pub = cfg.get("signer_pubkey") or derive_pub_from_signer_file(signer_file)
    data_size_filter = None
    v2_pref = True  # prefer GPA-v2/paged mode
    # internal sweep cache
    last_sweep = []

    while True:
        print_header(cfg, signer_pub, idl is not None, data_size_filter, v2_pref)
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
        print(" ─" * 30)
        print(" [20]  ✳ Prepare Position  → manifest (prepare_position)")
        print(" [21]  💰 Create Deposit    → manifest (create_deposit)")
        print(" [22]  💸 Create Withdrawal → manifest (create_withdrawal)")
        print(" [23]  🧾 Create Order      → manifest (create_order_v2)")
        print(" [24]  📂 Show outbox path")
        print(f" [0]   {ICONS['exit']} Exit")
        choice = input("Select: ").strip()
        if not choice:
            continue

        try:
            if choice == "0":
                print("bye.")
                return
            elif choice == "1":
                rpc = cfg.get("sol_rpc")
                if not rpc:
                    print(f"{ICONS['warn']} RPC not set in config.")
                    input("<enter>")
                    continue
                try:
                    res = rpc_call(rpc, "getHealth", [])
                    print(json.dumps(res, indent=2) if not isinstance(res, str) else res)
                except Exception as e:
                    print(f"{ICONS['warn']} RPC error: {e}")
                input("\n<enter>")
            elif choice == "2":
                pid = input("Store Program ID: ").strip()
                if pid:
                    cfg["store_program_id"] = pid
                    # persist
                    pathlib.Path(CONFIG_PATH).write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                    print(f"{ICONS['ok']} Store PID saved.")
                input("<enter>")
            elif choice == "3":
                sf = input(f"Signer file path [{signer_file}]: ").strip() or signer_file
                cfg["signer_file"] = sf
                signer_pub = derive_pub_from_signer_file(sf)
                if signer_pub:
                    cfg["signer_pubkey"] = signer_pub
                    pathlib.Path(CONFIG_PATH).write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                    print(f"{ICONS['ok']} Derived signer pub: {signer_pub}")
                else:
                    print(f"{ICONS['warn']} Could not derive signer pubkey from file.")
                input("<enter>")
            elif choice == "4":
                # Markets (paged) -> just show sample pubkeys
                rpc = cfg.get("sol_rpc")
                pid = cfg.get("store_program_id")
                if not (rpc and pid):
                    print(f"{ICONS['warn']} RPC or store PID missing.")
                    input("<enter>"); continue
                limit = cfg.get("limit", 100)
                page = cfg.get("page", 1)
                filters = {}
                if data_size_filter:
                    filters["dataSize"] = data_size_filter
                try:
                    accs = gpa_v2_get_program_accounts(rpc, pid, limit=limit, page=page, filters=filters if v2_pref else None)
                    # accs is list of dicts with pubkey
                    sample = [a.get("pubkey") for a in accs[:10]] if isinstance(accs, list) else []
                    summary = pretty_summary_raw_accounts(sample, len(accs) if isinstance(accs, list) else 0, [], rpc)
                    print(json.dumps(summary, indent=2))
                except Exception as e:
                    print(f"{ICONS['warn']} Error calling getProgramAccounts: {e}")
                input("<enter>")
            elif choice == "5":
                # positions from signer: sweep for accounts and show sample
                rpc = cfg.get("sol_rpc"); pid = cfg.get("store_program_id")
                if not (rpc and pid and signer_pub):
                    print(f"{ICONS['warn']} Ensure RPC/store/signer are set.")
                    input("<enter>"); continue
                off = cfg.get("owner_offset", 8)
                try:
                    # quick probe via memcmp (owner offset)
                    cfg_filters = {"filters":[{"memcmp":{"offset": off, "bytes": signer_pub}}], "limit":cfg.get("limit", 100), "page":cfg.get("page", 1)}
                    accs = rpc_call(rpc, "getProgramAccounts", [pid, {"encoding":"base64","commitment":"confirmed","limit":cfg.get("limit",100),"page":cfg.get("page",1),"filters":[{"memcmp":{"offset":off,"bytes":signer_pub}}]}])
                    if not isinstance(accs, list):
                        accs = accs or []
                    sample = [a.get("pubkey") for a in accs[:10]]
                    print(json.dumps(pretty_summary_raw_accounts(sample, len(accs), [], rpc), indent=2))
                except Exception as e:
                    print(f"{ICONS['warn']} Error reading positions: {e}")
                input("<enter>")
            elif choice == "6":
                pk = input("Enter pubkey: ").strip()
                if not pk:
                    input("<enter>"); continue
                rpc = cfg.get("sol_rpc")
                try:
                    res = rpc_call(rpc, "getAccountInfo", [pk, {"encoding":"base64"}])
                    print(json.dumps(res, indent=2))
                except Exception as e:
                    print(f"{ICONS['warn']} {e}")
                input("<enter>")
            elif choice == "7":
                # paging owner offset
                l = input(f"limit [{cfg.get('limit',100)}]: ").strip()
                p = input(f"page [{cfg.get('page',1)}]: ").strip()
                off = input(f"owner-offset [{cfg.get('owner_offset',8)}]: ").strip()
                if l: cfg["limit"] = int(l)
                if p: cfg["page"] = int(p)
                if off: cfg["owner_offset"] = int(off)
                pathlib.Path(CONFIG_PATH).write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                print(f"{ICONS['ok']} Paging updated.")
                input("<enter>")
            elif choice == "8":
                # quick sweep offsets
                rpc = cfg.get("sol_rpc"); pid = cfg.get("store_program_id")
                owner = signer_pub
                if not (rpc and pid and owner):
                    print(f"{ICONS['warn']} Ensure RPC, store PID and signer pub are set.")
                    input("<enter>"); continue
                offsets = [0,8,16,24,32,40,48,56,64,72,80,96,112,128]
                out = []
                for off in offsets:
                    n = memcmp_probe_count(rpc, pid, owner, off, page_limit=cfg.get("limit",100))
                    out.append((off, n))
                last_sweep = out
                print(json.dumps({"mode": "v2" if v2_pref else "v1", "sweep": out}, indent=2))
                input("<enter>")
            elif choice == "9":
                # show first match raw (if sweep produced something)
                rpc = cfg.get("sol_rpc"); pid = cfg.get("store_program_id")
                owner = signer_pub
                if not last_sweep:
                    print(f"{ICONS['warn']} No sweep results in memory. Run [8] first.")
                    input("<enter>"); continue
                # find first offset with >0
                offset = next((o for o,c in last_sweep if c>0), None)
                if offset is None:
                    print("No matches found in last sweep.")
                    input("<enter>"); continue
                try:
                    res = rpc_call(rpc, "getProgramAccounts", [pid, {"encoding":"base64","commitment":"confirmed","limit":10,"page":1,"filters":[{"memcmp":{"offset":offset,"bytes":owner}}]}])
                    print(json.dumps(res[:2] if isinstance(res, list) else res, indent=2))
                except Exception as e:
                    print(f"{ICONS['warn']} {e}")
                input("<enter>")
            elif choice == "10":
                v2_pref = not v2_pref
                print(f"{ICONS['ok']} V2 preference now {'on' if v2_pref else 'off'}.")
                input("<enter>")
            elif choice == "11":
                ds = input("dataSize filter (enter number to set, blank to clear): ").strip()
                data_size_filter = int(ds) if ds else None
                print(f"{ICONS['ok']} dataSize filter set to {data_size_filter}")
                input("<enter>")
            elif choice == "12":
                # pick best offset from last_sweep and apply to config
                if not last_sweep:
                    print(f"{ICONS['warn']} Need a sweep first (menu 8).")
                    input("<enter>"); continue
                best = max(last_sweep, key=lambda t: t[1])
                if best[1] == 0:
                    print("No positive matches to apply.")
                    input("<enter>"); continue
                cfg["owner_offset"] = best[0]
                pathlib.Path(CONFIG_PATH).write_text(json.dumps(cfg, indent=2), encoding="utf-8")
                print(f"{ICONS['ok']} Applied owner_offset={best[0]} (matched {best[1]} accounts).")
                input("<enter>")
            elif choice in ("20","21","22","23"):
                # build manifest for instruction
                mapping = {
                    "20": "prepare_position",
                    "21": "create_deposit",
                    "22": "create_withdrawal",
                    "23": "create_order_v2"
                }
                inst = mapping[choice]
                idl = load_idl() or {}
                prefill_accounts = None
                if inst == "create_order_v2":
                    store_account = cfg.get("store_account")
                    signer_prefill = signer_pub or derive_pub_from_signer_file(cfg.get("signer_file", str(ROOT / "signer.txt")))
                    prefill_accounts = {}
                    if signer_prefill:
                        prefill_accounts["authority"] = signer_prefill
                    if store_account:
                        prefill_accounts["store"] = store_account
                    prefill_accounts["tokenProgram"] = TOKEN_PROGRAM_CLASSIC
                fp, manifest = write_manifest(inst, idl, prefill_accounts=prefill_accounts)
                print(f"{ICONS['ok']} Manifest created: {fp}")
                print(f"• 🧾 Instruction : {inst}")
                account_entries = manifest.get("accounts", []) if isinstance(manifest, dict) else []
                acc_count = len(account_entries)
                filled_count = sum(1 for a in account_entries if a.get("pubkey"))
                pending_count = acc_count - filled_count
                args_count = len(manifest.get("args", [])) if isinstance(manifest, dict) else 0
                print(f"• 🧩 Accounts    : {acc_count} total → {filled_count} filled, {pending_count} pending")
                print(f"• 🧷 Args        : {args_count}")
                print(f"• 🔑 Discriminator (hex): {compute_anchor_discriminator(inst)}")
                print(f"• 📂 Outbox      : {OUTBOX_DIR}")
                input("<enter>")
            elif choice == "24":
                print(str(OUTBOX_DIR.resolve()))
                input("<enter>")
            else:
                print("Unknown selection.")
                input("<enter>")
        except Exception as e:
            print(f"{ICONS['warn']} Unexpected error: {e}")
            input("<enter>")

def main():
    interactive_menu()

if __name__ == "__main__":
    main()
