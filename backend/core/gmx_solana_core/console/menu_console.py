# -*- coding: utf-8 -*-
"""
GMX-Solana Interactive Console (Option A + builders)

What this file gives you
------------------------
• Main menu with discovery tools (positions/markets), manifest creators, and an Order Wizard.
• No external deps required (uses urllib). If 'solders' is available, we'll use it to derive PDAs.
• Robust config/session management; paths normalized to pathlib.Path (fixes .mkdir() crash).
• Order Wizard shows "Order Status" with green checks, guided fills, arg prompts, and simulate cmd.
• Refresh/Validate now shows wallet pubkey & scan context (owner/pubkey, offsets, limits, page, PID).

Config file (JSON)
------------------
Default: C:\\sonic7\\gmx_solana_console.json
Keys we read/write:
{
  "sol_rpc": "...",
  "store_program_id": "Gmso1uvJnLbawvw7yezdfCDcPydwW2s2iqG3w6MDucLo",
  "idl_path": "C:\\sonic7\\backend\\core\\gmx_solana_core\\idl\\gmsol-store.json",
  "signer_file": "C:\\sonic7\\signer.txt",
  "signer_pubkey": "C9JAHcK...",
  "owner_offset": 24,
  "limit": 100,
  "page": 1,
  "v2_preference": true,
  "datasize_filter": null,
  "outbox": "C:\\sonic7\\outbox",
  "store_account": "<detected store account>",
  "default_position": "<chosen position>",
  "default_market": "<chosen market>",
  "order_pda_recipe": [
      {"literal":"order"},
      {"pubkey":"position"},
      {"pubkey":"market"}
  ]
}

Manifests
---------
We write timestamped skeletons to outbox:
  YYYYMMDD_HHMMSS_create_order_v2.json
and keep helper routines to prefill accounts/args.

RPC
---
We use urllib to POST jsonrpc to the configured endpoint. For Helius:
  https://mainnet.helius-rpc.com/?api-key=YOURKEY

Author’s goal: keep things practical, not precious.
"""

from __future__ import annotations

import json
import sys
import time
import base64
import hashlib
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Optional PDA derivation via solders if present
try:
    from solders.pubkey import Pubkey as _SoldersPubkey  # type: ignore
    HAVE_SOLDERS = True
except Exception:
    _SoldersPubkey = None  # type: ignore
    HAVE_SOLDERS = False

# ------------------------------- Constants -------------------------------

DEFAULT_CFG_PATH = Path(r"C:\sonic7\gmx_solana_console.json")
DEFAULT_OUTBOX   = Path(r"C:\sonic7\outbox")
DEFAULT_IDL      = Path(r"C:\sonic7\backend\core\gmx_solana_core\idl\gmsol-store.json")
DEFAULT_SIGNER   = Path(r"C:\sonic7\signer.txt")
DEFAULT_STORE_PID = "Gmso1uvJnLbawvw7yezdfCDcPydwW2s2iqG3w6MDucLo"
SPL_TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

B58_ALPHABET = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")

ORDER_ARGS_KEYS = [
    "sizeDelta", "collateralDelta", "orderKind", "priceType",
    "triggerPriceX32", "slippageBps", "ttlSeconds"
]

# ------------------------------- Utilities -------------------------------

def _is_base58_pubkey(s: str) -> bool:
    if not isinstance(s, str):
        return False
    if not (32 <= len(s) <= 50):
        return False
    return all(c in B58_ALPHABET for c in s)

def _press_enter() -> None:
    try:
        input("<enter>")
    except KeyboardInterrupt:
        pass

def _print_boxed(title: str) -> None:
    title = title.strip()
    bar   = "─" * max(6, len(title) + 2)
    print(" " + bar)
    print(f" {title}")
    print(" " + bar)

def _sha256(data: bytes) -> bytes:
    h = hashlib.sha256()
    h.update(data)
    return h.digest()

def _anchor_account_disc_b64(name: str) -> str:
    # 8-byte discriminator = first 8 bytes of sha256("account:<Name>")
    h = _sha256(f"account:{name}".encode("ascii"))
    return base64.b64encode(h[:8]).decode("ascii")

def _anchor_ix_disc_hex(name: str) -> str:
    # 8-byte instruction discriminator = first 8 bytes of sha256("global:<ix>")
    h = _sha256(f"global:{name}".encode("ascii"))
    return h[:8].hex()

def _now_ts() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def _rpc_post(rpc_url: str, method: str, params: list) -> Any:
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": method, "params": params
    }).encode("utf-8")
    req = Request(rpc_url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            j = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raise RuntimeError(f"RPC {method} HTTP error: {e.code}") from e
    except URLError as e:
        raise RuntimeError(f"RPC {method} network error: {e.reason}") from e

    if "error" in j and j["error"]:
        raise RuntimeError(f"RPC {method} error: {j['error']}")
    return j.get("result")

# ------------------------------- Session -------------------------------

@dataclass
class Session:
    config_path: Path = DEFAULT_CFG_PATH
    sol_rpc: str = ""
    store_pid: str = DEFAULT_STORE_PID
    idl_path: Path = DEFAULT_IDL
    signer_file: Path = DEFAULT_SIGNER
    signer_pubkey: str = ""
    owner_offset: int = 24
    limit: int = 100
    page: int = 1
    v2_preference: bool = True
    datasize_filter: Optional[int] = None
    outbox: Path = DEFAULT_OUTBOX
    # discovered/saved
    store_account: str = ""
    default_position: str = ""
    default_market: str = ""
    order_pda_recipe: Optional[List[Dict[str, Any]]] = None

    def __init__(self) -> None:
        # Load config JSON if exists
        if self.config_path.exists():
            try:
                raw = json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception:
                raw = {}
        else:
            raw = {}

        # Assign with defaults if missing
        self.sol_rpc        = raw.get("sol_rpc", self.sol_rpc)
        self.store_pid      = raw.get("store_program_id", self.store_pid)
        self.signer_pubkey  = raw.get("signer_pubkey", self.signer_pubkey)
        self.owner_offset   = int(raw.get("owner_offset", self.owner_offset))
        self.limit          = int(raw.get("limit", self.limit))
        self.page           = int(raw.get("page", self.page))
        self.v2_preference  = bool(raw.get("v2_preference", self.v2_preference))
        self.datasize_filter= raw.get("datasize_filter", self.datasize_filter)

        self.store_account  = raw.get("store_account", self.store_account)
        self.default_position = raw.get("default_position", self.default_position)
        self.default_market   = raw.get("default_market", self.default_market)
        self.order_pda_recipe = raw.get("order_pda_recipe", self.order_pda_recipe)

        # Normalize pathlike values (this fixes the .mkdir() crash)
        self.config_path = Path(raw.get("config_path", str(self.config_path)))
        self.idl_path    = Path(raw.get("idl_path", str(self.idl_path)))
        self.signer_file = Path(raw.get("signer_file", str(self.signer_file)))
        try:
            self.outbox = Path(raw.get("outbox", str(self.outbox)))
        except TypeError:
            self.outbox = DEFAULT_OUTBOX

        # Ensure outbox exists
        self.outbox.mkdir(parents=True, exist_ok=True)

    def persist(self) -> None:
        obj = {
            "config_path": str(self.config_path),
            "sol_rpc": self.sol_rpc,
            "store_program_id": self.store_pid,
            "idl_path": str(self.idl_path),
            "signer_file": str(self.signer_file),
            "signer_pubkey": self.signer_pubkey,
            "owner_offset": int(self.owner_offset),
            "limit": int(self.limit),
            "page": int(self.page),
            "v2_preference": bool(self.v2_preference),
            "datasize_filter": self.datasize_filter,
            "outbox": str(self.outbox),
            "store_account": self.store_account,
            "default_position": self.default_position,
            "default_market": self.default_market,
            "order_pda_recipe": self.order_pda_recipe,
        }
        self.config_path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

# ------------------------------- RPC helpers -------------------------------

def _rpc_health(sess: Session) -> str:
    try:
        slot = _rpc_post(sess.sol_rpc, "getSlot", [{"commitment": "confirmed"}])
        return f"RPC ok. Current slot: {slot}"
    except Exception as e:
        return f"RPC health error: {e}"

def _list_positions_valid(sess: Session, limit: int = 200) -> List[str]:
    """
    Positions filtered by memcmp(owner_offset == signer_pubkey).
    """
    if not sess.signer_pubkey or not _is_base58_pubkey(sess.signer_pubkey):
        return []
    filt = {
        "encoding": "base64",
        "commitment": "confirmed",
        "filters": [
            {"memcmp": {"offset": int(sess.owner_offset), "bytes": sess.signer_pubkey}}
        ],
        "limit": int(limit)
    }
    res = _rpc_post(sess.sol_rpc, "getProgramAccounts", [sess.store_pid, filt])
    pubs: List[str] = []
    if isinstance(res, list):
        for a in res:
            pk = a.get("pubkey")
            if pk and _is_base58_pubkey(pk):
                pubs.append(pk)
    return pubs

def _list_markets(rpc: str, program_id: str, limit: int = 1000) -> List[str]:
    """
    Markets by discriminator "Market".
    """
    disc_b64 = _anchor_account_disc_b64("Market")
    cfg = {
        "encoding": "base64",
        "commitment": "confirmed",
        "dataSlice": {"offset": 0, "length": 8},
        "limit": int(limit),
    }
    res = _rpc_post(rpc, "getProgramAccounts", [program_id, cfg])
    pubs: List[str] = []
    if isinstance(res, list):
        for a in res:
            acct = a.get("account", {})
            data = acct.get("data")
            b64 = None
            if isinstance(data, list):
                b64 = data[0]
            elif isinstance(data, str):
                b64 = data
            if b64 == disc_b64:
                pk = a.get("pubkey")
                if pk and _is_base58_pubkey(pk):
                    pubs.append(pk)
    return pubs

def _detect_store_account(rpc: str, program_id: str) -> Optional[str]:
    disc_b64 = _anchor_account_disc_b64("Store")
    cfg = {
        "encoding": "base64",
        "commitment": "confirmed",
        "dataSlice": {"offset": 0, "length": 8},
    }
    res = _rpc_post(rpc, "getProgramAccounts", [program_id, cfg])
    if isinstance(res, list):
        for a in res:
            acct = a.get("account", {})
            data = acct.get("data")
            b64 = data[0] if isinstance(data, list) else data
            if b64 == disc_b64:
                pk = a.get("pubkey")
                if pk and _is_base58_pubkey(pk):
                    return pk
    return None

def _get_account_info(rpc: str, pubkey: str) -> Optional[dict]:
    try:
        res = _rpc_post(rpc, "getAccountInfo", [pubkey, {"encoding": "base64"}])
        return res.get("value")
    except Exception:
        return None

# ------------------------------- Manifest helpers -------------------------------

def _latest_order_manifest(sess: Session) -> Optional[Path]:
    files = sorted(sess.outbox.glob("*_create_order_v2.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

def _load_manifest(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _save_manifest(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def _acc_get(man: Dict[str, Any], name: str) -> Optional[str]:
    acc = man.get("accounts")
    if isinstance(acc, dict):
        return acc.get(name)
    if isinstance(acc, list):
        for it in acc:
            if it.get("name") == name:
                return it.get("pubkey")
    return None

def _acc_set(man: Dict[str, Any], name: str, value: str) -> None:
    if not value:
        return
    acc = man.get("accounts")
    if isinstance(acc, dict):
        acc[name] = value
        return
    if isinstance(acc, list):
        for it in acc:
            if it.get("name") == name:
                it["pubkey"] = value
                return
        # not present, append
        acc.append({"name": name, "pubkey": value, "isMut": False, "isSigner": False})
        return
    # None? Make a dict
    man["accounts"] = {name: value}

def _manifest_has_all_accounts(man: Dict[str, Any]) -> Tuple[bool, Dict[str, bool]]:
    needed = ["authority", "store", "position", "order", "market", "tokenProgram"]
    got: Dict[str, bool] = {}
    all_ok = True
    for n in needed:
        v = _acc_get(man, n)
        ok = bool(v and _is_base58_pubkey(v)) if n != "tokenProgram" else bool(v)
        got[n] = ok
        if not ok:
            all_ok = False
    return all_ok, got

def _manifest_has_args(man: Dict[str, Any]) -> bool:
    args = man.get("args")
    if not isinstance(args, dict):
        return False
    for k in ORDER_ARGS_KEYS:
        if k not in args:
            return False
    return True

def _write_order_skeleton(sess: Session) -> Path:
    """
    Create a timestamped create_order_v2 skeleton manifest and prefill authority/store/tokenProgram if known.
    """
    ts = _now_ts()
    path = sess.outbox / f"{ts}_create_order_v2.json"
    man = {
        "instruction": "create_order_v2",
        "discriminator_hex": _anchor_ix_disc_hex("create_order_v2"),
        "accounts": {
            "authority": "",
            "store": "",
            "position": "",
            "order": "",
            "market": "",
            "tokenProgram": ""
        },
        "args": {
            "sizeDelta": 0,
            "collateralDelta": 0,
            "orderKind": 0,
            "priceType": 0,
            "triggerPriceX32": "0",
            "slippageBps": 0,
            "ttlSeconds": 0
        }
    }
    # prefill easy bits
    if sess.signer_pubkey and _is_base58_pubkey(sess.signer_pubkey):
        man["accounts"]["authority"] = sess.signer_pubkey
    if sess.store_account and _is_base58_pubkey(sess.store_account):
        man["accounts"]["store"] = sess.store_account
    man["accounts"]["tokenProgram"] = SPL_TOKEN_PROGRAM

    _save_manifest(path, man)
    return path

def _prefill_latest(sess: Session) -> Optional[Path]:
    mf = _latest_order_manifest(sess)
    if not mf:
        return None
    man = _load_manifest(mf)
    if sess.signer_pubkey and not _acc_get(man, "authority"):
        _acc_set(man, "authority", sess.signer_pubkey)
    if sess.store_account and not _acc_get(man, "store"):
        _acc_set(man, "store", sess.store_account)
    if sess.default_position and not _acc_get(man, "position"):
        _acc_set(man, "position", sess.default_position)
    if sess.default_market and not _acc_get(man, "market"):
        _acc_set(man, "market", sess.default_market)
    if not _acc_get(man, "tokenProgram"):
        _acc_set(man, "tokenProgram", SPL_TOKEN_PROGRAM)
    _save_manifest(mf, man)
    return mf

# ------------------------------- PDA derivation -------------------------------

def _expand_seed_value(seed_spec: Dict[str, Any], sess: Session, man: Optional[Dict[str, Any]]) -> Optional[bytes]:
    """
    Convert a seed spec into bytes.
    Accepts:
      {"literal":"order"}
      {"utf8":"something"}
      {"u8":123}
      {"pubkey":"position"}    # position/market/authority keywords
      {"pubkey":"<actual base58>"}
    """
    if "literal" in seed_spec:
        return seed_spec["literal"].encode("utf-8")
    if "utf8" in seed_spec:
        return seed_spec["utf8"].encode("utf-8")
    if "u8" in seed_spec:
        v = int(seed_spec["u8"]) & 0xFF
        return bytes([v])
    if "pubkey" in seed_spec:
        val = seed_spec["pubkey"]
        if val in ("position", "market", "authority"):
            pk = None
            if man is not None:
                pk = _acc_get(man, val)
            if not pk and val == "position":
                pk = sess.default_position
            if not pk and val == "market":
                pk = sess.default_market
            if not pk and val == "authority":
                pk = sess.signer_pubkey
        else:
            pk = val
        if pk and _is_base58_pubkey(pk) and HAVE_SOLDERS:
            try:
                return bytes(_SoldersPubkey.from_string(pk))
            except Exception:
                return None
        # If we don't have solders, we cannot derive bytes of pubkey robustly; return ascii bytes
        if pk and _is_base58_pubkey(pk):
            return pk.encode("ascii")
    return None

def _derive_order_pda(sess: Session, recipe: List[Dict[str, Any]], man: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    If 'solders' is available, derive a PDA via Pubkey.find_program_address.
    """
    if not HAVE_SOLDERS:
        return None
    if not sess.store_pid or not _is_base58_pubkey(sess.store_pid):
        return None
    try:
        program = _SoldersPubkey.from_string(sess.store_pid)
    except Exception:
        return None

    seeds: List[bytes] = []
    for s in recipe:
        b = _expand_seed_value(s, sess, man)
        if b is None:
            return None
        seeds.append(b)

    try:
        pda, bump = _SoldersPubkey.find_program_address(seeds, program)  # type: ignore
        return str(pda)
    except Exception:
        return None

# ------------------------------- Display helpers -------------------------------

def _print_header(sess: Session) -> None:
    print("="*71)
    print("         🌊 GMX-Solana Interactive Console (Option A + builders)")
    print("="*71)
    print(f" 🩺 RPC        : {sess.sol_rpc or '(unset)'}")
    print(f" 🏦 Store PID  : {sess.store_pid}")
    print(f" 📝 Signer File: {str(sess.signer_file)}")
    print(f" 👤 Signer Pub : {sess.signer_pubkey or '(unset)'}")
    print(f" 🧭 OwnerOff   : {sess.owner_offset:>2}   📦 limit={sess.limit}  🧺 page={sess.page}")
    ds = f"dataSize={sess.datasize_filter}" if sess.datasize_filter else "dataSize=(none)"
    v2 = "on" if sess.v2_preference else "off"
    print(f" 🔎 Filters    : {ds}  V2={v2}")
    print(f" ⚙️  Config JSON: {str(sess.config_path)}")
    print(f" 📂 Outbox     : {str(sess.outbox)}")
    if sess.store_account:
        print(f" 🛰 Store acct : {sess.store_account}")
    print("-"*72)

def _status_checks(sess: Session) -> Tuple[Dict[str, bool], Optional[Path], Dict[str, Any]]:
    checks: Dict[str, bool] = {}
    checks["rpc_signer"] = bool(sess.sol_rpc and sess.signer_pubkey and _is_base58_pubkey(sess.signer_pubkey))
    checks["store_saved"] = bool(sess.store_account and _is_base58_pubkey(sess.store_account))

    mf = _latest_order_manifest(sess)
    checks["manifest_exists"] = bool(mf and mf.exists())

    acc_ok = False
    args_ok = False
    acc_flags: Dict[str, bool] = {k: False for k in ["authority","store","position","order","market","tokenProgram"]}
    if checks["manifest_exists"]:
        man = _load_manifest(mf)  # type: ignore
        acc_ok, acc_flags = _manifest_has_all_accounts(man)
        args_ok = _manifest_has_args(man)
    checks["accounts_ok"] = acc_ok
    checks["args_ok"] = args_ok

    return checks, mf, acc_flags

def _print_order_status(sess: Session) -> None:
    checks, mf, acc_flags = _status_checks(sess)
    print("  📊 Order Status")
    print("  " + "─"*66)
    print(f"  {'✅' if checks['rpc_signer'] else '❌'} RPC & Signer pubkey")
    print(f"  {'✅' if checks['store_saved'] else '❌'} Store account saved")
    if mf:
        print(f"  ✅ Manifest exists   ℹ️  {str(mf)}")
    else:
        print( "  ❌ Manifest exists")
    # Accounts line
    acct_line = []
    for name in ["authority","store","position","market","order","tokenProgram"]:
        ok = acc_flags.get(name, False)
        acct_line.append(("✅ " if ok else "❌ ") + name)
    print("  Accounts  : " + " ".join(acct_line))
    print("  Args      : " + ("✅ " if checks["args_ok"] else "❌ ") +
          ", ".join(ORDER_ARGS_KEYS))
    print("  " + "─"*66)
    if checks["rpc_signer"] and checks["store_saved"] and checks["manifest_exists"] and checks["accounts_ok"] and checks["args_ok"]:
        print("  ✅ Ready — simulate then add --send when clean.")
    else:
        print("  ⚠️ Not ready — fill red items")

def _print_order_details(sess: Session) -> None:
    mf = _latest_order_manifest(sess)
    print("  🧾 Order Details")
    print("  " + "─"*41)
    if not mf:
        print("  (no manifest yet)")
        return
    man = _load_manifest(mf)
    def pr_acc(label, key):
        val = _acc_get(man, key) or "(unset)"
        tick = "✅" if (val != "(unset)") else "❌"
        print(f"  {tick} {label:<14}: {val}")
    pr_acc("👤 authority", "authority")
    pr_acc("🛰 store", "store")
    pr_acc("🎯 position", "position")
    pr_acc("🧭 market", "market")
    pr_acc("🔑 order PDA", "order")
    pr_acc("🧪 tokenProgram", "tokenProgram")
    print("  " + "─"*41)
    args = man.get("args", {})
    def pr_arg(label, key):
        v = args.get(key, "(unset)")
        print(f"  ✅ {label:<21}: {v}") if key in args else print(f"  ❌ {label:<21}: (unset)")
    pr_arg("📏 Position size change", "sizeDelta")
    pr_arg("💰 Collateral change", "collateralDelta")
    pr_arg("🎛️ Order kind (enum)", "orderKind")
    pr_arg("🏷 Price type (enum)", "priceType")
    pr_arg("🎯 Trigger price x32", "triggerPriceX32")
    pr_arg("🧪 Allowed slippage (bps)", "slippageBps")
    pr_arg("⏱ Time-to-live (s)", "ttlSeconds")

# ------------------------------- Pickers & actions -------------------------------

def _pick_from_list(title: str, items: List[str]) -> Optional[str]:
    if not items:
        return None
    print("")
    print(title)
    for i, it in enumerate(items, 1):
        print(f"  [{i}] {it}")
    try:
        sel = input("Pick #: ").strip()
    except KeyboardInterrupt:
        return None
    if not sel.isdigit():
        return None
    idx = int(sel)
    if idx < 1 or idx > len(items):
        return None
    return items[idx - 1]

def _action_pick_position(sess: Session) -> None:
    print("⏳ Scanning VALID positions…")
    pubs = _list_positions_valid(sess, limit=200)
    if not pubs:
        print("⚠️  No positions; try Sweep Offsets in main menu.")
        _press_enter()
        return
    choice = _pick_from_list("Select Position:", pubs)
    if not choice:
        return
    sess.default_position = choice
    sess.persist()
    print(f"✅ Saved default_position: {choice}")
    _press_enter()

def _action_pick_market(sess: Session) -> None:
    print("⏳ Listing markets…")
    mkts = _list_markets(sess.sol_rpc, sess.store_pid, limit=1000)
    if not mkts:
        print("⚠️  No markets found.")
        _press_enter()
        return
    choice = _pick_from_list("Select Market:", mkts)
    if not choice:
        return
    sess.default_market = choice
    sess.persist()
    print(f"✅ Saved default_market: {choice}")
    _press_enter()

def _action_prefill_latest(sess: Session) -> None:
    mf = _prefill_latest(sess)
    if not mf:
        print("⚠️  No order manifest found. Use [23] to create one first.")
    else:
        print(f"✅ Prefilled: {str(mf)}")
    _press_enter()

def _action_paste_order_pda(sess: Session) -> None:
    mf = _latest_order_manifest(sess)
    if not mf:
        print("⚠️  No manifest yet. Create one with [23].")
        _press_enter()
        return
    man = _load_manifest(mf)
    try:
        val = input("Paste Order PDA pubkey: ").strip()
    except KeyboardInterrupt:
        return
    if not _is_base58_pubkey(val):
        print("⚠️  Not a base58 pubkey.")
        _press_enter()
        return
    _acc_set(man, "order", val)
    _save_manifest(mf, man)
    print(f"✅ Saved order PDA to {str(mf)}")
    _press_enter()

def _action_edit_args(sess: Session) -> None:
    mf = _latest_order_manifest(sess)
    if not mf:
        print("⚠️  No manifest yet. Create one with [23].")
        _press_enter()
        return
    man = _load_manifest(mf)
    if "args" not in man or not isinstance(man["args"], dict):
        man["args"] = {}
    args = man["args"]

    def prompt_u(label: str, maxbits: int, default: int = 0) -> int:
        rng = {16: 65535, 32: 4294967295, 64: 18446744073709551615}[maxbits]
        while True:
            try:
                s = input(f"{label} [default {default}]: ").strip()
            except KeyboardInterrupt:
                return default
            if s == "":
                return default
            try:
                v = int(s, 10)
                if 0 <= v <= rng:
                    return v
            except ValueError:
                pass
            print(f"Enter 0..{rng}.")

    def prompt_u128(label: str, default: str = "0") -> str:
        while True:
            try:
                s = input(f"{label} [default {default}]: ").strip()
            except KeyboardInterrupt:
                return default
            if s == "":
                return default
            if s.isdigit():
                return s
            print("Digits only for u128.")

    print("\nOrder arg helpers:")
    print("  • sizeDelta (u64): change in position size in contract units (set 0 if none).")
    print("  • collateralDelta (u64): change in collateral (set 0 if none).")
    print("  • orderKind (u16): enum (e.g., 0=Market, 1=Limit, 2=Trigger; confirm in IDL/docs).")
    print("  • priceType (u16): enum (e.g., 0=Mark, 1=Mid, 2=Last; confirm in IDL/docs).")
    print("  • triggerPriceX32 (u128): fixed-point price * 2^32 (0 for not-applicable).")
    print("  • slippageBps (u16): allowed slippage in basis points (default 50 = 0.50%).")
    print("  • ttlSeconds (u32): order expiry window (e.g., 300 for 5 minutes).")
    print("")

    # Recommended defaults for ease-of-use
    args["sizeDelta"]        = prompt_u("sizeDelta (u64)", 64, default=int(args.get("sizeDelta", 0)))
    args["collateralDelta"]  = prompt_u("collateralDelta (u64)", 64, default=int(args.get("collateralDelta", 0)))
    args["orderKind"]        = prompt_u("orderKind (u16)", 16, default=int(args.get("orderKind", 0)))
    args["priceType"]        = prompt_u("priceType (u16)", 16, default=int(args.get("priceType", 0)))
    args["triggerPriceX32"]  = prompt_u128("triggerPriceX32 (u128)", default=str(args.get("triggerPriceX32","0")))
    args["slippageBps"]      = prompt_u("slippageBps (u16)", 16, default=int(args.get("slippageBps", 50)))
    args["ttlSeconds"]       = prompt_u("ttlSeconds (u32)", 32, default=int(args.get("ttlSeconds", 300)))

    _save_manifest(mf, man)
    print(f"✅ Args saved: {str(mf)}")
    _press_enter()

def _action_print_simulate(sess: Session) -> None:
    mf = _latest_order_manifest(sess)
    if not mf:
        print("⚠️  No manifest yet. Create one with [23].")
        _press_enter()
        return
    print("\n▶️  Simulate (no send):")
    cmd = (
        f'python C:\\sonic7\\scripts\\gmsol_build_and_send_v2.py send-manifest '
        f'--rpc "{sess.sol_rpc}" '
        f'--program {sess.store_pid} '
        f'--idl {str(sess.idl_path)} '
        f'--signer-mnemonic-file {str(sess.signer_file)} '
        f'--manifest {str(mf)}'
    )
    print(cmd)
    print("Add --send when simulate is clean.")
    _press_enter()

def _action_detect_store(sess: Session) -> None:
    print("⏳ Detecting Store account by discriminator…")
    pk = _detect_store_account(sess.sol_rpc, sess.store_pid)
    if not pk:
        print("⚠️  No Store account found.")
        _press_enter()
        return
    sess.store_account = pk
    sess.persist()
    print(f"✅ store_account: {pk}")
    _press_enter()

def _action_refresh_validate(sess: Session) -> None:
    print("⏳ Refreshing positions/markets…")
    # Show context (wallet & scan params)
    print(f"   👤 Owner (signer pubkey): {sess.signer_pubkey or '(unset)'}")
    print(f"   🧭 OwnerOff: {sess.owner_offset}   📦 limit={sess.limit}  🧺 page={sess.page}")
    print(f"   🏦 Store PID: {sess.store_pid}")

    valid_pos = _list_positions_valid(sess, limit=200)
    mkts      = _list_markets(sess.sol_rpc, sess.store_pid, limit=200)

    cleared = []
    if sess.default_position and sess.default_position not in valid_pos:
        sess.default_position = ""; cleared.append("default_position")
    if sess.default_market and sess.default_market not in mkts:
        sess.default_market = ""; cleared.append("default_market")
    sess.persist()

    print(f"✅ Positions: {len(valid_pos)}  Markets: {len(mkts)}")
    print(("🧹 Cleared: " + ", ".join(cleared)) if cleared else "🟢 Defaults look good.")
    _press_enter()

# ------------------------------- Order Wizard -------------------------------

def _run_order_wizard(sess: Session) -> None:
    while True:
        print("\n" + "─"*70)
        print("  🧩  Order Wizard")
        print("─"*70)
        print(f"  🛰 store_account : {sess.store_account or '(not set)'}")
        print(f"  📌 def_position  : {sess.default_position or '(not set)'}")
        print(f"  🧭 def_market    : {sess.default_market or '(not set)'}")
        print("─"*70)
        _print_order_status(sess)
        print("─"*70)
        _print_order_details(sess)
        print("─"*70)
        print("  [1]  🔍 Detect & save Store")
        print("  [2]  📋 Pick Position (save default)")
        print("  [3]  🗺 Pick Market (save default)")
        print("  [4]  🧾 Prefill latest order manifest")
        print("  [5]  🔑 Derive Order PDA (recipe/auto)")
        print("  [6]  ✍️  Paste Order PDA (manual)")
        print("  [7]  ⚙️  Edit Args (typed values)")
        print("  [8]  📂 Show latest manifest path")
        print("  [9]  ▶️  Print simulate command")
        print("  [10] 🔎 Find Order PDA (scan & pick)  (manual check)")
        print("  [0]  ↩️  Back")
        try:
            choice = input("Select: ").strip()
        except KeyboardInterrupt:
            return

        if choice == "0":
            return
        elif choice == "1":
            _action_detect_store(sess)
        elif choice == "2":
            _action_pick_position(sess)
        elif choice == "3":
            _action_pick_market(sess)
        elif choice == "4":
            _action_prefill_latest(sess)
        elif choice == "5":
            _wizard_derive_pda(sess)
        elif choice == "6":
            _action_paste_order_pda(sess)
        elif choice == "7":
            _action_edit_args(sess)
        elif choice == "8":
            mf = _latest_order_manifest(sess)
            print(str(mf) if mf else "(no manifest)")
            _press_enter()
        elif choice == "9":
            _action_print_simulate(sess)
        elif choice == "10":
            _wizard_find_order_pda(sess)
        else:
            print("Unknown choice.")

def _wizard_derive_pda(sess: Session) -> None:
    mf = _latest_order_manifest(sess)
    man = _load_manifest(mf) if mf else None

    cfg_recipe = sess.order_pda_recipe

    if not cfg_recipe:
        print("\nNo order_pda_recipe in config.")
        print("1) Auto-derive (try common seeds)")
        print('2) Paste a recipe JSON (e.g. [{"literal":"order"},{"pubkey":"position"},{"pubkey":"market"}])')
        print("0) Cancel")
        try:
            mode = input("Choose [1/2/0]: ").strip()
        except KeyboardInterrupt:
            return
        if mode == "0":
            return
        if mode == "2":
            try:
                raw = input("Paste recipe JSON: ").strip()
            except KeyboardInterrupt:
                return
            try:
                cfg_recipe = json.loads(raw)
            except Exception as e:
                print(f"Invalid JSON: {e}")
                _press_enter()
                return
        else:
            # Auto recipes to try
            recipes = [
                [{"literal":"order"},{"pubkey":"position"},{"pubkey":"market"}],
                [{"literal":"order"},{"pubkey":"position"}],
                [{"literal":"order"},{"pubkey":"market"}],
                [{"literal":"order"},{"pubkey":"authority"},{"pubkey":"position"}]
            ]
            tried = []
            for r in recipes:
                tried.append(r)
                pda = _derive_order_pda(sess, r, man)
                if pda and _get_account_info(sess.sol_rpc, pda):
                    # Found a live account at this PDA — likely correct
                    cfg_recipe = r
                    sess.order_pda_recipe = r
                    sess.persist()
                    _acc_set(man, "order", pda)
                    if mf and man:
                        _save_manifest(mf, man)
                    print(f"✅ Derived Order PDA: {pda}")
                    _press_enter()
                    return
            print("⚠️ No valid Order PDA found via auto-recipes.\nTried:\n")
            for r in tried:
                print("  " + json.dumps(r))
            _press_enter()
            return

    # At this point we have a recipe (from cfg or pasted)
    pda = _derive_order_pda(sess, cfg_recipe, man)
    if not pda:
        print("⚠️ Could not derive PDA (need 'solders' installed or check recipe/seeds).")
        _press_enter()
        return
    _acc_set(man, "order", pda)
    if mf and man:
        _save_manifest(mf, man)
    sess.order_pda_recipe = cfg_recipe
    sess.persist()
    print(f"✅ Derived Order PDA: {pda}")
    _press_enter()

def _wizard_find_order_pda(sess: Session) -> None:
    """
    Minimal helper when derivation isn't possible: lets you paste a few candidates and checks
    which one actually exists on-chain. Saves the first good one.
    """
    mf = _latest_order_manifest(sess)
    if not mf:
        print("⚠️  No manifest yet. Create one with [23].")
        _press_enter()
        return
    man = _load_manifest(mf)
    print("\nPaste candidate Order PDA pubkeys (blank line to stop).")
    good = None
    while True:
        try:
            s = input("PDA: ").strip()
        except KeyboardInterrupt:
            return
        if s == "":
            break
        if not _is_base58_pubkey(s):
            print("  Not base58; skip.")
            continue
        info = _get_account_info(sess.sol_rpc, s)
        if info:
            good = s
            print("  ✅ Exists on-chain.")
            break
        else:
            print("  ❌ Not found.")
    if good:
        _acc_set(man, "order", good)
        _save_manifest(mf, man)
        print(f"✅ Saved order PDA to {str(mf)}")
    _press_enter()

# ------------------------------- Main menu actions -------------------------------

def _menu_markets(sess: Session) -> None:
    mkts = _list_markets(sess.sol_rpc, sess.store_pid, limit=sess.limit)
    print(json.dumps({"markets": mkts[:min(50, len(mkts))], "count": len(mkts)}, indent=2))
    _press_enter()

def _menu_positions_from_signer(sess: Session) -> None:
    pubs = _list_positions_valid(sess, limit=sess.limit)
    print(json.dumps({
        "matched_account_count": len(pubs),
        "sample_pubkeys": pubs[:min(20, len(pubs))]
    }, indent=2))
    _press_enter()

def _menu_account_info(sess: Session) -> None:
    try:
        pk = input("Enter pubkey: ").strip()
    except KeyboardInterrupt:
        return
    if not _is_base58_pubkey(pk):
        print("⚠️ Not a base58 pubkey.")
        _press_enter(); return
    info = _get_account_info(sess.sol_rpc, pk)
    print(json.dumps(info or {"error": "not found"}, indent=2))
    _press_enter()

def _menu_set_paging(sess: Session) -> None:
    def ask_int(prompt: str, default: int) -> int:
        try:
            s = input(f"{prompt} [{default}]: ").strip()
        except KeyboardInterrupt:
            return default
        if s == "":
            return default
        try:
            return int(s)
        except ValueError:
            return default
    sess.limit = ask_int("limit", sess.limit)
    sess.page  = ask_int("page", sess.page)
    sess.owner_offset = ask_int("owner_offset", sess.owner_offset)
    sess.persist()
    print("✅ Saved paging.")
    _press_enter()

def _menu_sweep_offsets(sess: Session) -> None:
    print("Sweeping offsets (0..96 step 8) for any hit…")
    found = []
    for off in range(0, 104, 8):
        try:
            filt = {
                "encoding": "base64",
                "commitment": "confirmed",
                "filters": [{"memcmp": {"offset": off, "bytes": sess.signer_pubkey}}],
                "limit": 5
            }
            res = _rpc_post(sess.sol_rpc, "getProgramAccounts", [sess.store_pid, filt])
            if isinstance(res, list) and len(res) > 0:
                found.append(off)
        except Exception:
            pass
        time.sleep(0.05)
    if found:
        print("💡 Offsets with hits:", found)
        sess.owner_offset = found[0]
        sess.persist()
        print(f"✅ Auto-applied owner_offset={sess.owner_offset}")
    else:
        print("⚠️  No hits across sweep.")
    _press_enter()

def _menu_show_first_raw(sess: Session) -> None:
    filt = {
        "encoding": "base64",
        "commitment": "confirmed",
        "filters": [{"memcmp": {"offset": sess.owner_offset, "bytes": sess.signer_pubkey}}],
        "limit": 1
    }
    res = _rpc_post(sess.sol_rpc, "getProgramAccounts", [sess.store_pid, filt])
    if isinstance(res, list) and res:
        print(json.dumps(res[0], indent=2))
    else:
        print("(no match)")
    _press_enter()

def _menu_write_skeleton(sess: Session, ix_name: str) -> None:
    if ix_name == "create_order_v2":
        path = _write_order_skeleton(sess)
        print(f"✅ Manifest created: {str(path)}")
        print("• 🧾 Instruction : create_order_v2")
        print("• 🧩 Accounts    : 6 total → prefilled authority/store/tokenProgram if known")
        print(f"• 🧷 Args        : {len(ORDER_ARGS_KEYS)}")
        print(f"• 🔑 Discriminator (hex): {_anchor_ix_disc_hex('create_order_v2')}")
        print(f"• 📂 Outbox      : {str(sess.outbox)}")
        _press_enter()
        return
    # Other ix (prepare_position / create_deposit / create_withdrawal) skeletons (minimal)
    ts = _now_ts()
    path = sess.outbox / f"{ts}_{ix_name}.json"
    minimal = {
        "instruction": ix_name,
        "discriminator_hex": _anchor_ix_disc_hex(ix_name),
        "accounts": {},
        "args": {}
    }
    _save_manifest(path, minimal)
    print(f"✅ {ix_name} manifest written to outbox (skeleton).")
    _press_enter()

def _menu_prefill_latest(sess: Session) -> None:
    _action_prefill_latest(sess)

def _menu_show_saved_discovery(sess: Session) -> None:
    out = {
        "store_account": sess.store_account or "(not set)",
        "default_position": sess.default_position or "(not set)",
        "default_market": sess.default_market or "(not set)",
        "order_pda_recipe": sess.order_pda_recipe or "(not set)"
    }
    print(json.dumps(out, indent=2))
    _press_enter()

def _menu_pick_position_valid(sess: Session) -> None:
    _action_pick_position(sess)

def _menu_pick_market_by_disc(sess: Session) -> None:
    _action_pick_market(sess)

def _menu_guided_prefill(sess: Session) -> None:
    # Minimal: pick and prefill
    _action_pick_position(sess)
    _action_pick_market(sess)
    _action_prefill_latest(sess)

def _menu_order_status(sess: Session) -> None:
    _print_order_status(sess)
    _print_order_details(sess)
    _press_enter()

def _menu_clear_defaults(sess: Session) -> None:
    sess.default_position = ""
    sess.default_market = ""
    sess.persist()
    print("✅ Cleared default position/market.")
    _press_enter()

# ------------------------------- Main menu loop -------------------------------

def run_menu() -> None:
    sess = Session()
    while True:
        _print_header(sess)
        print("  [1]  🩺 RPC health")
        print("  [2]  🏦 Set Store Program ID")
        print("  [3]  ✍️  Set Signer file path (and/or pubkey)")
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
        try:
            choice = input("Select: ").strip()
        except KeyboardInterrupt:
            print()
            return

        if choice == "0":
            return
        elif choice == "1":
            print(_rpc_health(sess)); _press_enter()
        elif choice == "2":
            try:
                v = input("Enter Store Program ID: ").strip()
            except KeyboardInterrupt:
                continue
            if _is_base58_pubkey(v):
                sess.store_pid = v; sess.persist()
                print("✅ Saved."); _press_enter()
            else:
                print("⚠️  Not a base58 pubkey."); _press_enter()
        elif choice == "3":
            try:
                p = input(f"Signer mnemonic file path [{str(sess.signer_file)}] (Enter to keep): ").strip()
            except KeyboardInterrupt:
                continue
            if p:
                sess.signer_file = Path(p)
            try:
                pk = input(f"Signer pubkey [{sess.signer_pubkey or '(unset)'}] (Enter to keep): ").strip()
            except KeyboardInterrupt:
                continue
            if pk:
                if _is_base58_pubkey(pk):
                    sess.signer_pubkey = pk
                else:
                    print("⚠️  Not a base58 pubkey.")
            sess.persist()
        elif choice == "4":
            _menu_markets(sess)
        elif choice == "5":
            _menu_positions_from_signer(sess)
        elif choice == "6":
            _menu_account_info(sess)
        elif choice == "7":
            _menu_set_paging(sess)
        elif choice == "8":
            _menu_sweep_offsets(sess)
        elif choice == "9":
            _menu_show_first_raw(sess)
        elif choice == "20":
            _menu_write_skeleton(sess, "prepare_position")
        elif choice == "21":
            _menu_write_skeleton(sess, "create_deposit")
        elif choice == "22":
            _menu_write_skeleton(sess, "create_withdrawal")
        elif choice == "23":
            _menu_write_skeleton(sess, "create_order_v2")
        elif choice == "24":
            print(str(sess.outbox)); _press_enter()
        elif choice == "25":
            _action_detect_store(sess)
        elif choice == "26":
            try:
                pk = input("Paste a POSITION pubkey to save: ").strip()
            except KeyboardInterrupt:
                continue
            if _is_base58_pubkey(pk):
                sess.default_position = pk; sess.persist(); print("✅ Saved.")
            else:
                print("⚠️  Not a base58 pubkey.")
            _press_enter()
        elif choice == "27":
            try:
                pk = input("Paste a MARKET pubkey to save: ").strip()
            except KeyboardInterrupt:
                continue
            if _is_base58_pubkey(pk):
                sess.default_market = pk; sess.persist(); print("✅ Saved.")
            else:
                print("⚠️  Not a base58 pubkey.")
            _press_enter()
        elif choice == "28":
            _menu_prefill_latest(sess)
        elif choice == "29":
            _menu_show_saved_discovery(sess)
        elif choice == "30":
            _menu_pick_position_valid(sess)
        elif choice == "31":
            _menu_pick_market_by_disc(sess)
        elif choice == "32":
            _menu_guided_prefill(sess)
        elif choice == "33":
            _run_order_wizard(sess)
        elif choice == "34":
            _menu_order_status(sess)
        elif choice == "35":
            _action_refresh_validate(sess)
        elif choice == "36":
            _menu_clear_defaults(sess)
        else:
            print("Unknown choice.")

# ------------------------------- Entrypoint -------------------------------

if __name__ == "__main__":
    run_menu()
