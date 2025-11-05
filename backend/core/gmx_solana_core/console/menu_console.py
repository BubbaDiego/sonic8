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
import glob
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

def _rpc_call_json(rpc_url: str, method: str, params: list, timeout: int = 10) -> dict:
    """Strict RPC call with short timeout and clear error text."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = Request(
        rpc_url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "gmx-console"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        raise RuntimeError(f"RPC {method} failed (timeout {timeout}s): {e}")
    if "error" in data:
        raise RuntimeError(f"RPC {method} error: {data['error']}")
    return data["result"]


def _rpc_call_json_safe(rpc_url: str, method: str, params: list, timeout: int = 10):
    """Non-throwing wrapper -> (result, error_str|None)."""
    try:
        return _rpc_call_json(rpc_url, method, params, timeout=timeout), None
    except Exception as e:
        return None, str(e)


class Session:
    """Mutable view over console JSON config with helper accessors."""

    def __init__(self, cfg: Dict[str, Any]):
        self._cfg = cfg
        self.rpc_http: str = cfg.get("sol_rpc", "") or ""
        self.store_pid: str = cfg.get("store_program_id", "") or ""
        self.store_account: str = cfg.get("store_account", "") or ""
        self.default_position: str = cfg.get("default_position", "") or ""
        self.default_market: str = cfg.get("default_market", "") or ""
        self.owner_offset: int = int(cfg.get("owner_offset", 8) or 0)
        self.limit: int = int(cfg.get("limit", 100) or 0)
        self.signer_pubkey: str = cfg.get("signer_pubkey", "") or ""

    def persist(self) -> None:
        self._cfg["sol_rpc"] = self.rpc_http
        if self.store_pid:
            self._cfg["store_program_id"] = self.store_pid
        self._cfg["store_account"] = self.store_account
        self._cfg["default_position"] = self.default_position
        self._cfg["default_market"] = self.default_market
        self._cfg["owner_offset"] = self.owner_offset
        self._cfg["limit"] = self.limit
        if self.signer_pubkey:
            self._cfg["signer_pubkey"] = self.signer_pubkey
        pathlib.Path(CONFIG_PATH).write_text(json.dumps(self._cfg, indent=2), encoding="utf-8")


_BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,}\Z")


def _is_base58(value: str) -> bool:
    return bool(isinstance(value, str) and _BASE58_RE.match(value or ""))


STORE_DISC = hashlib.sha256(b"account:Store").digest()[:8]
MARKET_DISC = hashlib.sha256(b"account:Market").digest()[:8]


def _anchor_disc_b64(name: str) -> str:
    disc = hashlib.sha256(f"account:{name}".encode()).digest()[:8]
    return base64.b64encode(disc).decode()


# --- ORDER discriminator (Anchor) ---
_ORDER_DISC_B64 = _anchor_disc_b64("Order")


def _account_has_disc(sess: "Session", pubkey: str, disc_b64: str) -> bool:
    if not (sess and sess.rpc_http and pubkey and disc_b64):
        return False
    res, err = _rpc_call_json_safe(
        sess.rpc_http,
        "getAccountInfo",
        [pubkey, {"encoding": "base64"}],
        timeout=6,
    )
    if err or not res or not res.get("value"):
        return False
    data = res["value"].get("data")
    b64 = data[0] if isinstance(data, list) and data else (data if isinstance(data, str) else None)
    if not b64:
        return False
    try:
        raw = base64.b64decode(b64)
        return base64.b64encode(raw[:8]).decode() == disc_b64
    except Exception:
        return False


def _list_orders_for_position(sess: "Session", position_b58: str, limit_per_offset: int = 200) -> List[str]:
    """Scan for Order accounts referencing a position via memcmp + discriminator."""
    if not (_is_base58(position_b58) and sess and sess.rpc_http and sess.store_pid):
        return []
    offsets_guess = [8, 24, 32, 40, 48, 56, 64, 72, 80, 96, 112, 128]
    seen: set[str] = set()
    out: List[str] = []
    for off in offsets_guess:
        cfg = {
            "encoding": "base64",
            "commitment": "confirmed",
            "limit": limit_per_offset,
            "page": 1,
            "filters": [{"memcmp": {"offset": int(off), "bytes": position_b58}}],
            "dataSlice": {"offset": 0, "length": 8},
        }
        res, err = _rpc_call_json_safe(
            sess.rpc_http,
            "getProgramAccountsV2",
            [sess.store_pid, cfg],
            timeout=8,
        )
        accts: List[dict] = []
        if not err and res:
            if isinstance(res, list):
                accts = res
            elif isinstance(res, dict):
                accts = res.get("value") or res.get("accounts") or []
        else:
            cfg2 = {
                "encoding": "base64",
                "commitment": "confirmed",
                "limit": limit_per_offset,
                "page": 1,
                "filters": [{"memcmp": {"offset": int(off), "bytes": position_b58}}],
                "dataSlice": {"offset": 0, "length": 8},
            }
            res2, err2 = _rpc_call_json_safe(
                sess.rpc_http,
                "getProgramAccounts",
                [sess.store_pid, cfg2],
                timeout=8,
            )
            if not err2 and isinstance(res2, list):
                accts = res2

        for entry in accts:
            pk = entry.get("pubkey") if isinstance(entry, dict) else None
            if not pk or pk in seen:
                continue
            if _account_has_disc(sess, pk, _ORDER_DISC_B64):
                out.append(pk)
                seen.add(pk)
    return out


def _decode_account_bytes(entry: Dict[str, Any]) -> Optional[bytes]:
    acct = entry.get("account", {}) if isinstance(entry, dict) else {}
    data = acct.get("data")
    raw = None
    if isinstance(data, list) and data:
        raw = data[0]
    elif isinstance(data, str):
        raw = data
    if not raw:
        return None
    try:
        return base64.b64decode(raw)
    except Exception:
        return None


def _find_store_account(rpc_url: str, program_id: str) -> Optional[str]:
    if not rpc_url or not program_id:
        return None
    cfg = {"encoding": "base64", "commitment": "confirmed", "limit": 200}
    res, err = _rpc_call_json_safe(rpc_url, "getProgramAccounts", [program_id, cfg], timeout=8)
    if err or not isinstance(res, list):
        return None
    for entry in res:
        raw = _decode_account_bytes(entry)
        if raw and raw.startswith(STORE_DISC):
            pk = entry.get("pubkey")
            if isinstance(pk, str):
                return pk
    return None


def _list_markets(rpc_url: str, program_id: str, limit: int = 100) -> List[str]:
    if not rpc_url or not program_id:
        return []
    cfg = {"encoding": "base64", "commitment": "confirmed", "limit": max(limit, 1)}
    res, err = _rpc_call_json_safe(rpc_url, "getProgramAccounts", [program_id, cfg], timeout=8)
    if err or not isinstance(res, list):
        return []
    out: List[str] = []
    for entry in res:
        raw = _decode_account_bytes(entry)
        if raw and raw.startswith(MARKET_DISC):
            pk = entry.get("pubkey")
            if isinstance(pk, str):
                out.append(pk)
    return out


def acc_get(manifest: Dict[str, Any], name: str) -> Optional[str]:
    accounts = manifest.get("accounts")
    if isinstance(accounts, dict):
        val = accounts.get(name)
        return val if isinstance(val, str) else None
    if isinstance(accounts, list):
        for acc in accounts:
            if isinstance(acc, dict) and acc.get("name") == name:
                val = acc.get("pubkey")
                return val if isinstance(val, str) else None
    return None


def ensure_accounts_list(manifest: Dict[str, Any]) -> None:
    accounts = manifest.get("accounts")
    if isinstance(accounts, list):
        return
    if isinstance(accounts, dict):
        manifest["accounts"] = [
            {"name": k, "pubkey": v}
            for k, v in accounts.items()
            if isinstance(k, str)
        ]
        return
    manifest["accounts"] = []


def acc_set(manifest: Dict[str, Any], name: str, value: str, mut: bool = False) -> None:
    accounts = manifest.get("accounts")
    if isinstance(accounts, dict):
        accounts[name] = value
        return
    if isinstance(accounts, list):
        for acc in accounts:
            if isinstance(acc, dict) and acc.get("name") == name:
                acc["pubkey"] = value
                if mut:
                    acc["isMut"] = True
                return
        entry = {"name": name, "pubkey": value}
        if mut:
            entry["isMut"] = True
        accounts.append(entry)
        return
    entry = {"name": name, "pubkey": value}
    if mut:
        entry["isMut"] = True
    manifest["accounts"] = [entry]


def _latest_order_manifest() -> Optional[str]:
    try:
        pattern = str(OUTBOX_DIR / "*_create_order_v2.json")
        paths = glob.glob(pattern)
        if not paths:
            return None
        return max(paths, key=os.path.getmtime)
    except Exception:
        return None

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
        for acc in manifest.get("accounts", []):
            name = acc.get("name")
            if name in prefill_accounts and not acc.get("pubkey"):
                acc["pubkey"] = prefill_accounts[name]
    fp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return fp, manifest


def _write_manifest_order_skeleton(sess: "Session") -> Optional[str]:
    """Create a create_order_v2 manifest with best-effort defaults."""
    idl = load_idl() or {}
    prefill: Dict[str, str] = {}
    if sess.signer_pubkey:
        prefill["authority"] = sess.signer_pubkey
    if sess.store_account:
        prefill["store"] = sess.store_account
    if sess.default_position:
        prefill["position"] = sess.default_position
    if sess.default_market:
        prefill["market"] = sess.default_market
    prefill["tokenProgram"] = SPL_TOKEN
    path, _ = write_manifest("create_order_v2", idl, prefill_accounts=prefill or None)
    return str(path)


def _auto_derive_order_pda(sess: "Session", manifest: Dict[str, Any]) -> Tuple[Optional[str], str]:
    ensure_accounts_list(manifest)
    existing = acc_get(manifest, "order")
    if _is_base58(existing or ""):
        return existing, f"ℹ️  Manifest already has order set: {existing}"
    pos = acc_get(manifest, "position") or sess.default_position or ""
    if not _is_base58(pos):
        return None, "⚠️  Need a valid position pubkey in manifest (accounts.position)."
    found = _list_orders_for_position(sess, pos, limit_per_offset=200)
    if not found:
        return None, "No valid Order PDA found via auto-recipes…"
    if len(found) == 1:
        return found[0], f"✅ Auto-derived Order PDA: {found[0]}"
    return None, f"⚠️  Multiple Order accounts ({len(found)}) reference this position. Use scan [10] to pick."


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
    res = _rpc_call_json(rpc, "getProgramAccounts", [program_id, cfg])
    # some RPCs (Helius) return list; others return dict — normalize
    if isinstance(res, dict) and "result" in res:
        return res["result"]
    return res if isinstance(res, list) else []

def memcmp_probe_count(rpc: str, program_id: str, owner_pubkey: str, offset: int, page_limit: int = 100) -> int:
    try:
        cfg = {"encoding": "base64", "commitment": "confirmed", "limit": page_limit, "page": 1,
               "filters": [{"memcmp": {"offset": offset, "bytes": owner_pubkey}}]}
        res = _rpc_call_json(rpc, "getProgramAccounts", [program_id, cfg])
        return len(res) if isinstance(res, list) else 0
    except Exception:
        return 0


def order_wizard_submenu(sess: "Session") -> None:
    def banner() -> None:
        print("─" * 70)
        print("  🧩  Order Wizard")
        print("─" * 70)
        print(f"  🛰 store_account : {sess.store_account or '(not set)'}")
        print(f"  📌 def_position  : {sess.default_position or '(not set)'}")
        print(f"  🧭 def_market    : {sess.default_market or '(not set)'}")
        print("─" * 70)

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        banner()
        print("  [1] 🔍 Detect & save Store")
        print("  [2] 📋 Pick Position (save default)")
        print("  [3] 🗺 Pick Market (save default)")
        print("  [4] 🧾 Prefill latest order manifest (authority/store/tokenProgram/position/market)")
        print("  [5] 🔑 Derive Order PDA (auto/manual)")
        print("  [6] ⚙️  Edit Args (typed values)")
        print("  [7] 📂 Show latest manifest path")
        print("  [8] ▶️  Print simulate command")
        print("  [10] 🔎 Find Order PDA (scan & pick)")
        print("  [0] ↩️  Back")
        sub = input("Select: ").strip()

        try:
            if sub == "0":
                return

            elif sub == "1":
                if sess.store_account:
                    print(f"🛰 Store already set: {sess.store_account}")
                    if input("Re-detect on chain? (y/N): ").strip().lower() not in ("y", "yes"):
                        input("<enter>")
                        continue
                print("⏳ Scanning for Store account (short timeout)…")
                store = _find_store_account(sess.rpc_http, sess.store_pid)
                if store:
                    sess.store_account = store
                    sess.persist()
                    print(f"✅ store_account: {store}")
                else:
                    print("⚠️  Could not find Store (network/timeout). Try again later.")
                input("<enter>")

            elif sub == "2":
                print("⏳ Scanning positions (page=1, owner_offset=", sess.owner_offset, ")…", sep="")
                cfg = {
                    "encoding": "base64",
                    "commitment": "confirmed",
                    "limit": sess.limit,
                    "page": 1,
                    "filters": [{"memcmp": {"offset": sess.owner_offset, "bytes": sess.signer_pubkey}}],
                }
                res, err = _rpc_call_json_safe(
                    sess.rpc_http,
                    "getProgramAccounts",
                    [sess.store_pid, cfg],
                    timeout=8,
                )
                if err:
                    print("⚠️  RPC failed:", err)
                    input("<enter>")
                    continue
                arr = res or []
                picks = [a.get("pubkey") for a in arr if isinstance(a, dict)]
                if not picks:
                    print("⚠️  No positions on this page. Run [8] Sweep then [12] Auto-apply 24, re-try.")
                    input("<enter>")
                    continue
                for i, p in enumerate(picks, 1):
                    print(f"  [{i}] {p}")
                sel = input("Pick #: ").strip()
                if not (sel.isdigit() and 1 <= int(sel) <= len(picks)):
                    print("Canceled.")
                    input("<enter>")
                    continue
                sess.default_position = picks[int(sel) - 1]
                sess.persist()
                print("✅ Saved default_position:", sess.default_position)
                input("<enter>")

            elif sub == "3":
                print("⏳ Listing markets (short timeout)…")
                markets = _list_markets(sess.rpc_http, sess.store_pid, limit=100)
                if not markets:
                    print("⚠️  No markets found (or timeout). Try again.")
                    input("<enter>")
                    continue
                for i, m in enumerate(markets, 1):
                    print(f"  [{i}] {m}")
                sel = input("Pick #: ").strip()
                if not (sel.isdigit() and 1 <= int(sel) <= len(markets)):
                    print("Canceled.")
                    input("<enter>")
                    continue
                sess.default_market = markets[int(sel) - 1]
                sess.persist()
                print("✅ Saved default_market:", sess.default_market)
                input("<enter>")

            elif sub == "4":
                mf = _latest_order_manifest()
                if not mf:
                    print("ℹ️  No order manifest yet. Run [23] once to create it.")
                    input("<enter>")
                    continue
                man = json.loads(pathlib.Path(mf).read_text(encoding="utf-8"))
                changed: List[str] = []
                if sess.signer_pubkey and not acc_get(man, "authority"):
                    acc_set(man, "authority", sess.signer_pubkey)
                    changed.append("authority")
                if sess.store_account and not acc_get(man, "store"):
                    acc_set(man, "store", sess.store_account)
                    changed.append("store")
                if not acc_get(man, "tokenProgram"):
                    acc_set(man, "tokenProgram", SPL_TOKEN)
                    changed.append("tokenProgram")
                if sess.default_position and not acc_get(man, "position"):
                    acc_set(man, "position", sess.default_position)
                    changed.append("position")
                if sess.default_market and not acc_get(man, "market"):
                    acc_set(man, "market", sess.default_market)
                    changed.append("market")
                pathlib.Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                print("✅ Prefilled:", mf)
                print("   🔧 fields:", ", ".join(changed) if changed else "(nothing)")
                input("<enter>")

            elif sub == "5":
                mf = _latest_order_manifest() or _write_manifest_order_skeleton(sess)
                if not mf:
                    print("ℹ️  Run [23] first.")
                    input("<enter>")
                    continue
                path = pathlib.Path(mf)
                if not path.exists():
                    print("⚠️  Manifest missing on disk. Run [23] to create it again.")
                    input("<enter>")
                    continue
                man = json.loads(path.read_text(encoding="utf-8"))
                ensure_accounts_list(man)
                print("  [1] Auto-derive via recipes")
                print("  [2] Paste Order PDA manually")
                mode = input("Select [1]: ").strip() or "1"
                if mode == "2":
                    op = input("Paste ORDER PDA pubkey: ").strip()
                    if not _is_base58(op):
                        print("⚠️  Not valid base58.")
                    else:
                        acc_set(man, "order", op, mut=True)
                        path.write_text(json.dumps(man, indent=2), encoding="utf-8")
                        print("✅ Wrote 'order' into manifest.")
                else:
                    pda, msg = _auto_derive_order_pda(sess, man)
                    print(msg)
                    if pda:
                        acc_set(man, "order", pda, mut=True)
                        path.write_text(json.dumps(man, indent=2), encoding="utf-8")
                        print("✅ Wrote 'order' into manifest.")
                    else:
                        pos_for_scan = acc_get(man, "position") or sess.default_position or ""
                        if not _is_base58(pos_for_scan):
                            print("⚠️  No position set. Use steps [2]/[4] first.")
                        elif input("Run Order PDA scan for this position now? (Y/n): ").strip().lower() in ("", "y", "yes"):
                            found = _list_orders_for_position(sess, pos_for_scan, limit_per_offset=200)
                            if found:
                                for i, pk in enumerate(found, 1):
                                    print(f"  [{i}] {pk}")
                                sel = input("Pick #: ").strip()
                                if sel.isdigit() and 1 <= int(sel) <= len(found):
                                    picked = found[int(sel) - 1]
                                    acc_set(man, "order", picked, mut=True)
                                    path.write_text(json.dumps(man, indent=2), encoding="utf-8")
                                    print("✅ Wrote 'order' into manifest.")
                                else:
                                    print("Canceled.")
                            else:
                                print("⚠️  Scanner found no Order accounts for this position.")
                input("<enter>")

            elif sub == "6":
                mf = _latest_order_manifest()
                if not mf:
                    print("ℹ️  Run [23] first.")
                    input("<enter>")
                    continue
                man = json.loads(pathlib.Path(mf).read_text(encoding="utf-8"))
                if "args" not in man or not isinstance(man["args"], dict):
                    man["args"] = {}

                def _u(prompt: str, cast=int, allow_empty: bool = True, as_str: bool = False):
                    s = input(prompt).strip()
                    if not s and allow_empty:
                        return "0" if as_str else 0
                    try:
                        return s if as_str else cast(s)
                    except Exception:
                        print("Bad input.")
                        return _u(prompt, cast, allow_empty, as_str)

                print("⚙️  Args: press Enter for 0")
                man["args"]["sizeDelta"] = int(_u("  sizeDelta (u64) [0]: ", int))
                man["args"]["collateralDelta"] = int(_u("  collateralDelta (u64) [0]: ", int))
                man["args"]["orderKind"] = int(_u("  orderKind (u16) [0]: ", int))
                man["args"]["priceType"] = int(_u("  priceType (u16) [0]: ", int))
                man["args"]["triggerPriceX32"] = _u("  triggerPriceX32 (u128) [0]: ", as_str=True)
                man["args"]["slippageBps"] = int(_u("  slippageBps (u16) [0]: ", int))
                man["args"]["ttlSeconds"] = int(_u("  ttlSeconds (u32) [0]: ", int))
                pathlib.Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                print("✅ Args updated.")
                input("<enter>")

            elif sub == "7":
                mf = _latest_order_manifest()
                print(mf or "(no manifest)")
                input("<enter>")

            elif sub == "8":
                mf = _latest_order_manifest()
                if not mf:
                    print("ℹ️  Run [23] first.")
                    input("<enter>")
                    continue
                print("\n▶️  Simulate (no send):")
                print(
                    rf'python C:\\sonic7\\scripts\\gmsol_build_and_send_v2.py send-manifest --rpc "{sess.rpc_http}" --program {sess.store_pid} --idl C:\\sonic7\\backend\\core\\gmx_solana_core\\idl\\gmsol-store.json --signer-mnemonic-file C:\\sonic7\\signer.txt --manifest {mf}'
                )
                print("Add --send when simulate is clean.")
                input("<enter>")

            elif sub == "10":
                mf = _latest_order_manifest() or _write_manifest_order_skeleton(sess)
                if not mf:
                    print("ℹ️  Run [23] first.")
                    input("<enter>")
                    continue
                path = pathlib.Path(mf)
                if not path.exists():
                    print("⚠️  Manifest missing on disk. Run [23] to create it again.")
                    input("<enter>")
                    continue
                man = json.loads(path.read_text(encoding="utf-8"))
                ensure_accounts_list(man)
                pos = acc_get(man, "position") or sess.default_position or ""
                if not _is_base58(pos):
                    print("⚠️  No position set. Use steps [2]/[4] first.")
                    input("<enter>")
                    continue
                print("⏳ Scanning for Order accounts that reference this position…")
                found = _list_orders_for_position(sess, pos, limit_per_offset=200)
                if not found:
                    print("⚠️  No Order accounts found for this position (or timeout).")
                    input("<enter>")
                    continue
                for i, pk in enumerate(found, 1):
                    print(f"  [{i}] {pk}")
                sel = input("Pick Order PDA #: ").strip()
                if not (sel.isdigit() and 1 <= int(sel) <= len(found)):
                    print("Canceled.")
                    input("<enter>")
                    continue
                picked = found[int(sel) - 1]
                acc_set(man, "order", picked, mut=True)
                path.write_text(json.dumps(man, indent=2), encoding="utf-8")
                print(f"✅ Wrote 'order' into manifest: {picked}")
                input("<enter>")

            else:
                print("Unknown selection.")
                input("<enter>")

        except Exception as e:
            print("Wizard error:", e)
            input("<enter>")

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
        print(" [25]  🧩 Order Wizard (guided defaults)")
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
                    res = _rpc_call_json(rpc, "getHealth", [])
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
                    accs = _rpc_call_json(rpc, "getProgramAccounts", [pid, {"encoding":"base64","commitment":"confirmed","limit":cfg.get("limit",100),"page":cfg.get("page",1),"filters":[{"memcmp":{"offset":off,"bytes":signer_pub}}]}])
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
                    res = _rpc_call_json(rpc, "getAccountInfo", [pk, {"encoding":"base64"}])
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
                    res = _rpc_call_json(rpc, "getProgramAccounts", [pid, {"encoding":"base64","commitment":"confirmed","limit":10,"page":1,"filters":[{"memcmp":{"offset":offset,"bytes":owner}}]}])
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
            elif choice == "25":
                order_wizard_submenu(Session(cfg))
                cfg = load_config()
                signer_file = cfg.get("signer_file", str(ROOT / "signer.txt"))
                signer_pub = cfg.get("signer_pubkey") or derive_pub_from_signer_file(signer_file)
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
