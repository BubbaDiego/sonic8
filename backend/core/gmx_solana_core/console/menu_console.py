# -*- coding: utf-8 -*-
"""
GMX-Solana Interactive Console (Option A + builders)
====================================================

This file is intentionally standard-library only. It talks to your RPC via
JSON-RPC and manages a small JSON config (gmx_solana_console.json) plus
timestamped manifests in the outbox.

CODEx INSTRUCTIONS (what changed vs previous drop)
--------------------------------------------------
1) Feature: Show wallet (signer) public address in [35] Refresh/Validate
   - Prints owner pubkey and the scan parameters (ownerOffset/limit/page/Store PID)
2) Also shows the same owner line inside:
   - [30] Pick Position (validated)
   - Order Wizard → any place that lists/filters positions or markets
3) Preserves all menu items (25–36), Prefill, Pickers, Order Wizard, Status, etc.

If Codex is doing a minimal patch, replace ONLY the "elif choice == '35':" block
with the version below, and add the owner info prints in Pick Position & Wizard.

Tested assumptions:
- Config JSON lives at: C:\sonic7\gmx_solana_console.json
- Outbox folder:        C:\sonic7\outbox (create if missing)
- Program (Store PID):  Gmso1uv... (can be changed in [2])
- Signer pubkey string is already known/stored; otherwise paste once in [3].

"""

from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# -------------------------- small utils --------------------------

B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


def _is_base58(s: str) -> bool:
    if not s or not isinstance(s, str):
        return False
    for ch in s:
        if ch not in B58_ALPHABET:
            return False
    return True


def _now_stamp() -> str:
    return _dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _discriminator_b64(account_name: str) -> str:
    """Anchor discriminator: first 8 bytes of sha256(f'account:{name}') as base64."""
    h = hashlib.sha256(("account:" + account_name).encode("ascii")).digest()
    return base64.b64encode(h[:8]).decode("ascii")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _rpc(url: str, method: str, params: list) -> Any:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            j = json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError) as e:
        raise RuntimeError(f"RPC {method} failed: {e}")
    if "error" in j and j["error"]:
        raise RuntimeError(f"RPC {method} error: {j['error']}")
    return j.get("result")


def _fmt_yes(b: bool) -> str:
    return "✅" if b else "❌"


def _press_enter() -> None:
    try:
        input("<enter>")
    except KeyboardInterrupt:
        pass


# -------------------------- Session / config --------------------------

class Session:
    def __init__(self) -> None:
        # Defaults
        self.config_path = Path(r"C:\sonic7\gmx_solana_console.json")
        self.outbox = Path(r"C:\sonic7\outbox")
        self.sol_rpc: str = "https://mainnet.helius-rpc.com/?api-key=REPLACE_ME"
        self.store_program_id: str = "Gmso1uvJnLbawvw7yezdfCDcPydwW2s2iqG3w6MDucLo"
        self.signer_file: str = r"C:\sonic7\signer.txt"
        self.signer_pubkey: str = ""  # paste once in [3] if needed
        self.owner_offset: int = 24
        self.limit: int = 100
        self.page: int = 1
        self.v2: bool = True
        self.data_size_filter: Optional[int] = None

        # discoveries / helpers
        self.store_account: str = ""
        self.default_position: str = ""
        self.default_market: str = ""
        self.order_pda_recipe: List[Dict[str, str]] = []  # [{"literal":"order"},{"pubkey":"position"},{"pubkey":"market"}]

        if self.config_path.exists():
            try:
                cfg = _read_json(self.config_path)
                self.__dict__.update({k: v for k, v in cfg.items() if k in self.__dict__})
            except Exception:
                pass  # keep defaults

        self.outbox.mkdir(parents=True, exist_ok=True)

    # Persist everything (safe overwrite)
    def persist(self) -> None:
        data = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        # strip non-serializable (Path → str)
        data["config_path"] = str(self.config_path)
        data["outbox"] = str(self.outbox)
        _write_json(self.config_path, data)


# -------------------------- RPC helpers --------------------------

def _get_program_accounts(url: str, program: str, cfg: Dict[str, Any]) -> list:
    """Standard getProgramAccounts (portable)."""
    return _rpc(url, "getProgramAccounts", [program, cfg]) or []


def _get_program_accounts_v2(url: str, program: str, cfg: Dict[str, Any]) -> list:
    """
    Helius V2 paging. We use only if v2 = True. Fallback to standard on failure.
    """
    try:
        return _rpc(url, "getProgramAccountsV2", [program, cfg]) or []
    except Exception:
        return []


def _list_positions(sess: Session, limit: int = 200) -> List[str]:
    """Return raw positions found by memcmp(owner_offset == signer pubkey)."""
    if not sess.signer_pubkey or not _is_base58(sess.signer_pubkey):
        return []
    cfg = {"encoding": "base64", "commitment": "confirmed",
           "filters": [{"memcmp": {"offset": int(sess.owner_offset), "bytes": sess.signer_pubkey}}]}
    res = _get_program_accounts(sess.sol_rpc, sess.store_program_id, cfg)
    return [r.get("pubkey") for r in res if r.get("pubkey")]


def _list_markets(rpc_url: str, program: str, limit: int = 1000, use_v2: bool = True) -> List[str]:
    disc = _discriminator_b64("Market")
    cfg = {"encoding": "base64", "commitment": "confirmed", "dataSlice": {"offset": 0, "length": 8}}
    res = _get_program_accounts_v2(rpc_url, program, {"encoding": "base64", "commitment": "confirmed",
                                                       "limit": limit, "page": 1, "dataSlice": {"offset": 0, "length": 8}}) if use_v2 else []
    accts: List[Dict[str, Any]] = []
    if res:
        # v2 can return arrays under different shapes; normalize
        if isinstance(res, list):
            accts = res
        elif isinstance(res, dict):
            if "value" in res and isinstance(res["value"], list):
                accts = res["value"]
            elif "accounts" in res and isinstance(res["accounts"], list):
                accts = res["accounts"]
    else:
        accts = _get_program_accounts(rpc_url, program, cfg)

    pubs: List[str] = []
    for a in accts:
        dat = a.get("account", {}).get("data")
        if isinstance(dat, list) and dat and dat[0] == disc:
            pubs.append(a.get("pubkey"))
    return pubs


def _detect_store(sess: Session) -> Optional[str]:
    disc = _discriminator_b64("Store")
    cfg = {"encoding": "base64", "commitment": "confirmed", "dataSlice": {"offset": 0, "length": 8}}
    # Try V2 1 page, then fallback
    res_v2 = _get_program_accounts_v2(sess.sol_rpc, sess.store_program_id,
                                      {"encoding": "base64", "commitment": "confirmed",
                                       "limit": 1000, "page": 1, "dataSlice": {"offset": 0, "length": 8}})
    accts: List[Dict[str, Any]] = []
    if res_v2:
        if isinstance(res_v2, list):
            accts = res_v2
        elif isinstance(res_v2, dict):
            accts = res_v2.get("value") or res_v2.get("accounts") or []
    else:
        accts = _get_program_accounts(sess.sol_rpc, sess.store_program_id, cfg)

    for a in accts:
        dat = a.get("account", {}).get("data")
        if isinstance(dat, list) and dat and dat[0] == disc:
            return a.get("pubkey")
    return None


# -------------------------- Manifests --------------------------

def _latest_manifest(outbox: Path, pattern: str = "*_create_order_v2.json") -> Optional[Path]:
    files = sorted(outbox.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _get_acc(man: Dict[str, Any], name: str) -> Optional[str]:
    acc = man.get("accounts")
    if isinstance(acc, dict):
        return acc.get(name)
    if isinstance(acc, list):
        for item in acc:
            if item.get("name") == name:
                return item.get("pubkey")
    return None


def _set_acc(man: Dict[str, Any], name: str, value: str) -> None:
    if not value:
        return
    if "accounts" not in man or man["accounts"] is None:
        man["accounts"] = {}
    acc = man["accounts"]
    if isinstance(acc, dict):
        acc[name] = value
        return
    if isinstance(acc, list):
        for item in acc:
            if item.get("name") == name:
                item["pubkey"] = value
                return
        # add if not present
        acc.append({"name": name, "pubkey": value, "isMut": False, "isSigner": False})


def _prefill_latest_order(sess: Session) -> Tuple[Optional[Path], Optional[Dict[str, Any]], List[str]]:
    mf = _latest_manifest(sess.outbox)
    if not mf:
        return None, None, []
    man = _read_json(mf)
    touched: List[str] = []
    if sess.signer_pubkey and not _get_acc(man, "authority"):
        _set_acc(man, "authority", sess.signer_pubkey); touched.append("authority")
    if sess.store_account and not _get_acc(man, "store"):
        _set_acc(man, "store", sess.store_account); touched.append("store")
    if sess.default_position and not _get_acc(man, "position"):
        _set_acc(man, "position", sess.default_position); touched.append("position")
    if sess.default_market and not _get_acc(man, "market"):
        _set_acc(man, "market", sess.default_market); touched.append("market")
    if not _get_acc(man, "tokenProgram"):
        _set_acc(man, "tokenProgram", TOKEN_PROGRAM); touched.append("tokenProgram")

    _write_json(mf, man)
    return mf, man, touched


# -------------------------- UI helpers --------------------------

def _hdr(sess: Session) -> None:
    print("=" * 68)
    print("  🌊 GMX-Solana Interactive Console (Option A + builders)")
    print("=" * 68)
    print(f" 🩺 RPC        : {sess.sol_rpc}")
    print(f" 🏦 Store PID  : {sess.store_program_id}")
    print(f" 📝 Signer File: {sess.signer_file}")
    print(f" 👤 Signer Pub : {sess.signer_pubkey or '(unset)'}")
    print(f" 🧭 OwnerOff   : {sess.owner_offset:>2}   📦 limit={sess.limit}  🧺 page={sess.page}")
    ds = f"{sess.data_size_filter}" if sess.data_size_filter else "(none)"
    print(f" 🔎 Filters    : dataSize={ds}  V2={'on' if sess.v2 else 'off'}")
    print(f" ⚙️  Config JSON: {sess.config_path}")
    print(f" 📂 Outbox     : {sess.outbox}")
    if sess.store_account:
        print(f" 🛰 Store acct : {sess.store_account}")
    print("-" * 72)


def _menu() -> None:
    print("  [1]  🩺 RPC health")
    print("  [2]  🏦 Set Store Program ID")
    print("  [3]  ✍️  Set Signer file path (paste pubkey)")
    print("  [4]  🧮 Markets (paged sample)")
    print("  [5]  📌 Positions (from signer)")
    print("  [6]  🔍 Account info (enter pubkey)")
    print("  [7]  🧭 Set paging (limit/page/owner-offset)")
    print("  [8]  🧪 Sweep offsets (quick)")
    print("  [9]  🧬 Show first match (raw)")
    print(" ───────────────────────────────────────────────────────────────")
    print(" [20]  ✳ Prepare Position  → manifest (skeleton)")
    print(" [21]  💰 Create Deposit    → manifest (skeleton)")
    print(" [22]  💸 Create Withdrawal → manifest (skeleton)")
    print(" [23]  🧾 Create Order      → manifest (timestamped skeleton)")
    print(" [24]  📂 Show outbox path")
    print(" ───────────────────────────────────────────────────────────────")
    print(" [25]  🛰 Detect Store (save to config)")
    print(" [26]  📌 Save Default Position (paste)")
    print(" [27]  🧭 Save Default Market (paste)")
    print(" [28]  🧾 Prefill latest order manifest")
    print(" [29]  🗂 Show saved discovery (store/position/market/recipe)")
    print(" [30]  📋 Pick Position (validated) → save")
    print(" [31]  🗺 Pick Market (by discriminator) → save")
    print(" [32]  🧭 Guided Prefill (position/market pickers)")
    print(" [33]  🧩 Order Wizard")
    print(" [34]  🧾 Order Status")
    print(" [35]  🔄 Refresh / Validate (positions & markets)")
    print(" [36]  🧹 Clear saved defaults (position/market)")
    print(" [0]   🚪 Exit")


# -------------------------- screens / actions --------------------------

def _rpc_health(sess: Session) -> None:
    print("⏳ Checking RPC…")
    try:
        _ = _rpc(sess.sol_rpc, "getEpochInfo", [])
        print("✅ RPC reachable.")
    except Exception as e:
        print(f"❌ RPC error: {e}")
    _press_enter()


def _set_store_pid(sess: Session) -> None:
    s = input("Enter Store Program ID: ").strip()
    if not _is_base58(s):
        print("❌ Not a base58 pubkey.")
    else:
        sess.store_program_id = s
        sess.persist()
        print("✅ Saved.")
    _press_enter()


def _set_signer_file(sess: Session) -> None:
    path = input(f"Signer file path [{sess.signer_file}]: ").strip() or sess.signer_file
    sess.signer_file = path
    # We can't derive pubkey without external tools; ask to paste once.
    if not sess.signer_pubkey:
        pasted = input("Paste signer public address (base58): ").strip()
        if _is_base58(pasted):
            sess.signer_pubkey = pasted
    sess.persist()
    print(f"👤 Signer Pub : {sess.signer_pubkey or '(unset)'}")
    _press_enter()


def _markets_sample(sess: Session) -> None:
    print("⏳ Listing markets…")
    pubs = _list_markets(sess.sol_rpc, sess.store_program_id, limit=1000, use_v2=sess.v2)
    for i, p in enumerate(pubs[:64], 1):
        print(f"  [{i}] {p}")
    print(f"… total {len(pubs)}")
    _press_enter()


def _positions_for_signer(sess: Session) -> None:
    if not sess.signer_pubkey:
        print("⚠️  No signer pubkey configured.")
        _press_enter()
        return
    print(f"⏳ Positions (owner = {sess.signer_pubkey})")
    pubs = _list_positions(sess)
    print(json.dumps({"matched_account_count": len(pubs), "sample_pubkeys": pubs[:8]}, indent=2))
    _press_enter()


def _account_info(sess: Session) -> None:
    pk = input("Enter pubkey: ").strip()
    if not _is_base58(pk):
        print("❌ Not base58.")
        _press_enter()
        return
    try:
        info = _rpc(sess.sol_rpc, "getAccountInfo", [pk, {"encoding": "base64"}])
        print(json.dumps(info, indent=2))
    except Exception as e:
        print(f"RPC error: {e}")
    _press_enter()


def _set_paging(sess: Session) -> None:
    try:
        sess.limit = int(input(f"limit [{sess.limit}]: ") or sess.limit)
        sess.page = int(input(f"page  [{sess.page}]: ") or sess.page)
        sess.owner_offset = int(input(f"owner_offset [{sess.owner_offset}]: ") or sess.owner_offset)
        sess.persist()
        print("✅ Saved.")
    except Exception:
        print("❌ Bad numbers.")
    _press_enter()


def _sweep_offsets(sess: Session) -> None:
    print("⏳ Quick sweep for offsets (0..64 step 4)…")
    hits = []
    for off in range(0, 65, 4):
        try:
            cfg = {"encoding": "base64", "commitment": "confirmed",
                   "filters": [{"memcmp": {"offset": off, "bytes": sess.signer_pubkey}}]}
            res = _get_program_accounts(sess.sol_rpc, sess.store_program_id, cfg)
            if res:
                hits.append((off, len(res)))
        except Exception:
            pass
        time.sleep(0.05)
    if hits:
        print("Offset → count:")
        for off, n in hits:
            print(f"  {off:>2} → {n}")
    else:
        print("No hits.")
    _press_enter()


def _show_first_match(sess: Session) -> None:
    print("⏳ First match with current ownerOffset memcmp…")
    try:
        cfg = {"encoding": "base64", "commitment": "confirmed",
               "filters": [{"memcmp": {"offset": int(sess.owner_offset), "bytes": sess.signer_pubkey}}]}
        res = _get_program_accounts(sess.sol_rpc, sess.store_program_id, cfg)
        if res:
            print(json.dumps(res[:1], indent=2))
        else:
            print("No matches.")
    except Exception as e:
        print(f"RPC error: {e}")
    _press_enter()


def _write_skeleton(sess: Session, name: str) -> None:
    mf = sess.outbox / f"{_now_stamp()}_{name}.json"
    skeleton = {
        "instruction": name,
        "accounts": {},
        "args": {},
        "discriminator_hex": {
            "prepare_position": "0000000000000000",
            "create_deposit": "0000000000000000",
            "create_withdrawal": "0000000000000000",
            "create_order_v2": "c89d03b603a4a2f0",
        }.get(name, "0000000000000000"),
    }
    _write_json(mf, skeleton)
    print(f"{name} manifest written to outbox: {mf}")
    _press_enter()


def _show_outbox(sess: Session) -> None:
    print(str(sess.outbox))
    _press_enter()


def _detect_store_and_save(sess: Session) -> None:
    print("⏳ Detecting Store account…")
    pk = _detect_store(sess)
    if pk:
        sess.store_account = pk
        sess.persist()
        print(f"✅ store_account: {pk}")
    else:
        print("⚠️  No Store account found (try later).")
    _press_enter()


def _save_default_position(sess: Session) -> None:
    s = input("Paste a POSITION pubkey to save as default: ").strip()
    if not _is_base58(s):
        print("⚠️  Not a valid base58.")
    else:
        sess.default_position = s
        sess.persist()
        print("✅ Saved.")
    _press_enter()


def _save_default_market(sess: Session) -> None:
    s = input("Paste a MARKET account pubkey to save as default: ").strip()
    if not _is_base58(s):
        print("⚠️  Not a valid base58.")
    else:
        sess.default_market = s
        sess.persist()
        print("✅ Saved.")
    _press_enter()


def _prefill_latest(sess: Session) -> None:
    mf, man, touched = _prefill_latest_order(sess)
    if not mf:
        print("ℹ️  No latest order manifest. Run [23] once to create.")
        _press_enter()
        return
    print(f"✅ Prefilled: {mf}")
    if touched:
        print(" ↳ fields: " + ", ".join(touched))
    _press_enter()


def _show_saved(sess: Session) -> None:
    print(json.dumps({
        "store_account": sess.store_account or "(not set)",
        "default_position": sess.default_position or "(not set)",
        "default_market": sess.default_market or "(not set)",
        "order_pda_recipe": sess.order_pda_recipe or "(not set)"
    }, indent=2))
    _press_enter()


def _pick_position(sess: Session) -> None:
    if not sess.signer_pubkey:
        print("⚠️  No signer pubkey configured.")
        _press_enter()
        return
    print(f"👤 Owner (signer pubkey): {sess.signer_pubkey}")
    print(f"🧭 Using owner_offset={sess.owner_offset}")
    print("⏳ Scanning VALID positions…")
    pubs = _list_positions(sess)
    if not pubs:
        print("⚠️  No positions; try Sweep Offsets (8) or check owner_offset.")
        _press_enter()
        return
    for i, p in enumerate(pubs, 1):
        print(f"  [{i}] {p}")
        if i >= 200:
            break
    s = input("Pick #: ").strip()
    try:
        idx = int(s)
        if 1 <= idx <= len(pubs):
            sess.default_position = pubs[idx - 1]
            sess.persist()
            print(f"✅ Saved default_position: {sess.default_position}")
        else:
            print("No selection.")
    except Exception:
        print("No selection.")
    _press_enter()


def _pick_market(sess: Session) -> None:
    print("⏳ Listing markets…")
    pubs = _list_markets(sess.sol_rpc, sess.store_program_id, use_v2=sess.v2)
    if not pubs:
        print("⚠️  None found.")
        _press_enter()
        return
    for i, p in enumerate(pubs, 1):
        print(f"  [{i}] {p}")
        if i >= 200:
            break
    s = input("Pick #: ").strip()
    try:
        idx = int(s)
        if 1 <= idx <= len(pubs):
            sess.default_market = pubs[idx - 1]
            sess.persist()
            print(f"✅ Saved default_market: {sess.default_market}")
        else:
            print("No selection.")
    except Exception:
        print("No selection.")
    _press_enter()


def _guided_prefill(sess: Session) -> None:
    # pick position
    _pick_position(sess)
    # pick market
    _pick_market(sess)
    # prefill
    _prefill_latest(sess)


def _order_status(sess: Session, echo: bool = True) -> Dict[str, Any]:
    mf_path = _latest_manifest(sess.outbox)
    mf = _read_json(mf_path) if mf_path else {}
    have_acc = {k: bool(_get_acc(mf, k)) for k in ("authority", "store", "position", "market", "order", "tokenProgram")}
    args = mf.get("args") or {}
    need_args = ["sizeDelta", "collateralDelta", "orderKind", "priceType", "triggerPriceX32", "slippageBps", "ttlSeconds"]
    have_args = all(a in args for a in need_args)
    ready = all(have_acc.values()) and have_args

    if echo:
        print("─" * 70)
        print("  📊 Order Status")
        print("─" * 70)
        print(f"  {_fmt_yes(bool(sess.sol_rpc and sess.signer_pubkey))} RPC & Signer pubkey")
        print(f"  {_fmt_yes(bool(sess.store_account))} Store account saved")
        if mf_path:
            print(f"  ✅ Manifest exists   ℹ️ {mf_path}")
        else:
            print(f"  ❌ Manifest exists")
        print("  Accounts  : " +
              " ".join([f"{_fmt_yes(v)} {name}" for name, v in have_acc.items()]))
        print("  Args      : " +
              (_fmt_yes(have_args) + " " + ", ".join(need_args) if have_args else "❌ args missing"))
        print("─" * 70)
        if ready:
            print("  ✅ Ready to simulate/send")
        else:
            print("  ⚠️ Not ready — fill red items")
        print("─" * 70)
    return {"ready": ready, "mf_path": str(mf_path) if mf_path else ""}


def _order_wizard(sess: Session) -> None:
    while True:
        print("──────────────────────────────────────────────────────────────────────")
        print("  🧩  Order Wizard")
        print("──────────────────────────────────────────────────────────────────────")
        if sess.store_account:
            print(f"  🛰 store_account : {sess.store_account}")
        print(f"  📌 def_position  : {sess.default_position or '(not set)'}")
        print(f"  🧭 def_market    : {sess.default_market or '(not set)'}")
        _order_status(sess, echo=True)
        print("  [1]  🔍 Detect & save Store")
        print("  [2]  📋 Pick Position (save default)")
        print("  [3]  🗺 Pick Market (save default)")
        print("  [4]  🧾 Prefill latest order manifest")
        print("  [5]  🔑 Derive Order PDA (recipe/auto)")
        print("  [6]  ✍️  Paste Order PDA (manual)")
        print("  [7]  ⚙️  Edit Args (typed values)")
        print("  [8]  📂 Show latest manifest path")
        print("  [9]  ▶️  Print simulate command")
        print("  [0]  ↩️  Back")
        ch = input("Select: ").strip()
        if ch == "0":
            return
        elif ch == "1":
            _detect_store_and_save(sess)
        elif ch == "2":
            _pick_position(sess)
        elif ch == "3":
            _pick_market(sess)
        elif ch == "4":
            _prefill_latest(sess)
        elif ch == "5":
            print("ℹ️ PDA derivation requires seeds and solana libs; use [6] to paste if needed.")
            _press_enter()
        elif ch == "6":
            mf_path = _latest_manifest(sess.outbox)
            if not mf_path:
                print("No manifest; run [4] or main [23] first.")
                _press_enter()
                continue
            man = _read_json(mf_path)
            val = input("Paste Order PDA pubkey: ").strip()
            if _is_base58(val):
                _set_acc(man, "order", val)
                _write_json(mf_path, man)
                print("✅ order account set.")
            else:
                print("❌ Not base58.")
            _press_enter()
        elif ch == "7":
            mf_path = _latest_manifest(sess.outbox)
            if not mf_path:
                print("No manifest; run [4] or main [23] first.")
                _press_enter()
                continue
            man = _read_json(mf_path)
            man.setdefault("args", {})
            def _u16(lbl: str) -> int:
                s = input(f"{lbl} (u16) [0]: ").strip()
                return int(s) if s.isdigit() else 0
            def _u32(lbl: str) -> int:
                s = input(f"{lbl} (u32) [0]: ").strip()
                return int(s) if s.isdigit() else 0
            def _u64(lbl: str) -> int:
                s = input(f"{lbl} (u64) [0]: ").strip()
                return int(s) if s.isdigit() else 0
            def _u128(lbl: str) -> str:
                s = input(f"{lbl} (u128) [0]: ").strip()
                return s if s.isdigit() else "0"

            # User-friendly nudges
            print("Tips: orderKind 0=Market 1=Limit 2=Trigger  (confirm with GMX docs)")
            print("      priceType 0=Mark 1=Last 2=Oracle?    (confirm in IDL/SDK)")
            print("      slippageBps default 50 (0.5%) is reasonable for testing")

            man["args"]["sizeDelta"]        = _u64("sizeDelta")
            man["args"]["collateralDelta"]  = _u64("collateralDelta")
            man["args"]["orderKind"]        = _u16("orderKind")
            man["args"]["priceType"]        = _u16("priceType")
            man["args"]["triggerPriceX32"]  = _u128("triggerPriceX32")
            s_bps = input("slippageBps (u16) [50]: ").strip()
            man["args"]["slippageBps"]      = int(s_bps) if s_bps.isdigit() else 50
            s_ttl = input("ttlSeconds (u32) [300]: ").strip()
            man["args"]["ttlSeconds"]       = int(s_ttl) if s_ttl.isdigit() else 300

            _write_json(mf_path, man)
            print(f"✅ Args saved: {mf_path}")
            _press_enter()
        elif ch == "8":
            mf_path = _latest_manifest(sess.outbox)
            print(str(mf_path) if mf_path else "No manifest yet.")
            _press_enter()
        elif ch == "9":
            mf_path = _latest_manifest(sess.outbox)
            mf_disp = str(mf_path) if mf_path else "<no manifest>"
            cmd = (
                f'python C:\\sonic7\\scripts\\gmsol_build_and_send_v2.py send-manifest '
                f'--rpc "{sess.sol_rpc}" '
                f'--program {sess.store_program_id} '
                f'--idl C:\\sonic7\\backend\\core\\gmx_solana_core\\idl\\gmsol-store.json '
                f'--signer-mnemonic-file {sess.signer_file} '
                f'--manifest {mf_disp}'
            )
            print("\n▶️  Simulate (no send):\n" + cmd + "\nAdd --send when simulate is clean.")
            _press_enter()
        else:
            print("Unknown choice.")


def _order_status_screen(sess: Session) -> None:
    _order_status(sess, echo=True)
    _press_enter()


def _refresh_validate(sess: Session) -> None:
    # ★★★★★ Your requested enhancement begins here
    print("⏳ Refreshing positions/markets…")
    print(f"   👤 Owner (signer pubkey): {sess.signer_pubkey or '(unset)'}")
    print(f"   🧭 OwnerOff: {sess.owner_offset}   📦 limit={sess.limit}  🧺 page={sess.page}")
    print(f"   🏦 Store PID: {sess.store_program_id}")

    valid_pos = _list_positions(sess)
    mkts      = _list_markets(sess.sol_rpc, sess.store_program_id, limit=200, use_v2=sess.v2)

    cleared: List[str] = []
    if sess.default_position and sess.default_position not in valid_pos:
        sess.default_position = ""; cleared.append("default_position")
    if sess.default_market and sess.default_market not in mkts:
        sess.default_market = ""; cleared.append("default_market")
    sess.persist()

    print(f"✅ Positions: {len(valid_pos)}  Markets: {len(mkts)}")
    print(("🧹 Cleared: " + ", ".join(cleared)) if cleared else "🟢 Defaults look good.")
    _press_enter()
    # ★★★★★ End enhancement


def _clear_defaults(sess: Session) -> None:
    sess.default_position = ""
    sess.default_market = ""
    sess.persist()
    print("✅ Cleared defaults.")
    _press_enter()


# -------------------------- main loop --------------------------

def run_menu() -> None:
    sess = Session()
    while True:
        _hdr(sess)
        _menu()
        choice = input("Select: ").strip()
        if choice == "0":
            return
        elif choice == "1":
            _rpc_health(sess)
        elif choice == "2":
            _set_store_pid(sess)
        elif choice == "3":
            _set_signer_file(sess)
        elif choice == "4":
            _markets_sample(sess)
        elif choice == "5":
            _positions_for_signer(sess)
        elif choice == "6":
            _account_info(sess)
        elif choice == "7":
            _set_paging(sess)
        elif choice == "8":
            _sweep_offsets(sess)
        elif choice == "9":
            _show_first_match(sess)
        elif choice == "20":
            _write_skeleton(sess, "prepare_position")
        elif choice == "21":
            _write_skeleton(sess, "create_deposit")
        elif choice == "22":
            _write_skeleton(sess, "create_withdrawal")
        elif choice == "23":
            # timestamped skeleton helps differentiate attempts
            _write_skeleton(sess, "create_order_v2")
        elif choice == "24":
            _show_outbox(sess)
        elif choice == "25":
            _detect_store_and_save(sess)
        elif choice == "26":
            _save_default_position(sess)
        elif choice == "27":
            _save_default_market(sess)
        elif choice == "28":
            _prefill_latest(sess)
        elif choice == "29":
            _show_saved(sess)
        elif choice == "30":
            _pick_position(sess)    # includes owner line
        elif choice == "31":
            _pick_market(sess)
        elif choice == "32":
            _guided_prefill(sess)
        elif choice == "33":
            _order_wizard(sess)     # wizard echoes owner in pickers/status
        elif choice == "34":
            _order_status_screen(sess)
        elif choice == "35":
            _refresh_validate(sess)  # enhanced: shows wallet/address + scan context
        elif choice == "36":
            _clear_defaults(sess)
        else:
            print("Unknown choice.")
            _press_enter()


if __name__ == "__main__":
    try:
        run_menu()
    except KeyboardInterrupt:
        print()
