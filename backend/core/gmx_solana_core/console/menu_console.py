# -*- coding: utf-8 -*-
"""
GMX-Solana Interactive Console (builders + discovery + pickers + Order Wizard + Status)
- JSON config only; default: C:\sonic7\gmx_solana_console.json
- Uses stdlib RPC (urllib) with short timeouts + clear messages
- Shape-safe manifest accounts (dict OR list of {"name","pubkey","isMut","isSigner"})

Main menu (kept & extended):
  [1]..[12] classic utilities (health, paging, memcmp sweep, show raw)
  [20]..[22] skeleton writers for prepare/deposit/withdraw
  [23]  create_order_v2 skeleton (timestamped)
  [24]  show outbox path
  [25]  Detect Store (save store_account)
  [26]  Save Default Position (paste)
  [27]  Save Default Market (paste)
  [28]  Prefill latest manifest (authority/store/tokenProgram/position/market)
  [29]  Show saved discovery (store/position/market/recipe)
  [30]  Pick Position (validated by discriminator) → save default
  [31]  Pick Market (by discriminator) → save default
  [32]  Guided Prefill (position/market pickers)
  [33]  Order Wizard (submenu)
  [34]  Order Status (✅/❌ checklist with READY banner)
  [35]  Refresh / Validate (positions & markets)     ← NEW
  [36]  Clear saved defaults (position/market)       ← NEW

Order Wizard adds:
  [10] 🔎 Find Order PDA (scan & pick)  ← scans chain for Order accounts referencing your Position
  [11] 🧹 Clear manifest (order/position) ← NEW

Optional config keys (C:\sonic7\gmx_solana_console.json):
  "order_pda_recipe": [
    {"literal":"order"},
    {"pubkey":"position"},
    {"pubkey":"market"}
  ],
  "order_defaults": { "slippageBps": 50, "ttlSeconds": 600 },
  "order_kind_map": { "DECREASE": 2, "INCREASE": 1 },
  "price_type_map": { "MARKET": 0, "TRIGGER": 1 }
"""
from __future__ import annotations
import os, re, json, time, glob, base64, hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from urllib.request import Request, urlopen

# Optional PDA derivation with solders
try:
    from solders.pubkey import Pubkey
    HAVE_SOLDERS = True
except Exception:
    HAVE_SOLDERS = False

# ------------ Constants & Paths ------------
ROOT         = Path(r"C:\sonic7")
DEFAULT_JSON = ROOT / "gmx_solana_console.json"
OUTBOX_DIR   = ROOT / "outbox"

# Store PROGRAM id (NOT a store state account)
STORE_PROG_ID = "Gmso1uvJnLbawvw7yezdfCDcPydwW2s2iqG3w6MDucLo"
SPL_TOKEN      = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

CHECK, CROSS, INFO, WARN, ROCKET = "✅", "❌", "ℹ️", "⚠️", "🚀"

# ------------ Small Utilities ------------
def pretty(x: Any) -> str:
    return json.dumps(x, indent=2, ensure_ascii=False)

def load_json(path: Path = DEFAULT_JSON) -> Dict[str, Any]:
    if not path.exists(): return {}
    try:    return json.loads(path.read_text(encoding="utf-8"))
    except: return {}

def save_json(obj: Dict[str, Any], path: Path = DEFAULT_JSON) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def _is_base58(s: str) -> bool:
    return isinstance(s, str) and len(s) >= 32 and re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]+", s or "") is not None

def _rpc_call_json(rpc_url: str, method: str, params: list, timeout: int = 8) -> dict:
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req  = Request(rpc_url, data=body, headers={"Content-Type":"application/json","User-Agent":"gmx-console"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        raise RuntimeError(f"RPC {method} failed (timeout {timeout}s): {e}")
    if "error" in data:
        raise RuntimeError(f"RPC {method} error: {data['error']}")
    return data["result"]

def _rpc_call_json_safe(rpc_url: str, method: str, params: list, timeout: int = 8):
    try:
        return _rpc_call_json(rpc_url, method, params, timeout=timeout), None
    except Exception as e:
        return None, str(e)

def _anchor_disc_b64(name: str) -> str:
    h = hashlib.sha256(f"account:{name}".encode("ascii")).digest()[:8]
    return base64.b64encode(h).decode()

# ------------ Defaults & Mapping (optional) ------------
def _cfg_defaults() -> Dict[str, int]:
    j = load_json(DEFAULT_JSON)
    d = j.get("order_defaults", {})
    return {
        "slippageBps": int(d.get("slippageBps", 50)),  # 0.50%
        "ttlSeconds":  int(d.get("ttlSeconds", 600)),  # 10 minutes
    }

def _cfg_maps() -> Dict[str, Dict[str, int]]:
    j = load_json(DEFAULT_JSON)
    return {
        "orderKind": j.get("order_kind_map", {}),  # name -> int
        "priceType": j.get("price_type_map", {}),  # name -> int
    }

# ------------ Signer Helpers (no crash) ------------
def derive_pub_from_signer_file(path: str) -> Optional[str]:
    """
    Minimal effort to get a pubkey string:
    - First line base58
    - JSON with 'pubkey' / 'publicKey'
    Returns None if unavailable.
    """
    p = Path(path)
    if not p.exists(): return None
    txt = p.read_text(encoding="utf-8", errors="ignore").strip()
    if not txt: return None
    line1 = txt.splitlines()[0].strip()
    if _is_base58(line1) and len(line1) in (43,44):
        return line1
    try:
        j = json.loads(txt)
        if isinstance(j, dict):
            for k in ("publicKey","pubkey","pubKey"):
                v = j.get(k)
                if isinstance(v, str) and _is_base58(v): return v
    except Exception:
        pass
    return None

# ------------ Manifest helpers (shape-safe) ------------
def acc_get(man: dict, key: str) -> Optional[str]:
    acc = man.get("accounts")
    if isinstance(acc, dict):  return acc.get(key)
    if isinstance(acc, list):
        for it in acc:
            if isinstance(it, dict) and it.get("name") == key:
                return it.get("pubkey") or ""
    return None

def acc_set(man: dict, key: str, value: str, *, mut=False, signer=False) -> None:
    if not value: return
    acc = man.get("accounts")
    if isinstance(acc, dict):
        acc[key] = value; return
    if isinstance(acc, list):
        for it in acc:
            if isinstance(it, dict) and it.get("name") == key:
                it["pubkey"] = value; return
        acc.append({"name": key, "pubkey": value, "isMut": bool(mut), "isSigner": bool(signer)})

def ensure_accounts_list(man: dict) -> None:
    acc = man.get("accounts")
    if isinstance(acc, list): return
    if isinstance(acc, dict):
        out = []
        for k, v in acc.items():
            out.append({"name": k, "pubkey": v, "isMut": False, "isSigner": False})
        man["accounts"] = out
        return
    man["accounts"] = []

# ------------ Scanning helpers (discriminators) ------------
def _find_accounts_by_disc(rpc: str, program: str, acc_name: str, page_limit=1000, max_pages=10) -> List[str]:
    disc_b64 = _anchor_disc_b64(acc_name)
    pubs: List[str] = []
    # GPA-V2 paged
    try:
        page = 1
        while page <= max_pages:
            cfg = {"encoding":"base64","commitment":"confirmed","limit":page_limit,"page":page,"dataSlice":{"offset":0,"length":8}}
            res = _rpc_call_json(rpc, "getProgramAccountsV2", [program, cfg])
            accts = []
            if isinstance(res, list): accts = res
            elif isinstance(res, dict): accts = res.get("value") or res.get("accounts") or []
            if not accts: break
            for a in accts:
                d = a.get("account",{}).get("data")
                b64 = d[0] if isinstance(d, list) and d else (d if isinstance(d, str) else None)
                if b64 == disc_b64:
                    pub = a.get("pubkey")
                    if pub and pub not in pubs: pubs.append(pub)
            if len(accts) < page_limit: break
            page += 1; time.sleep(0.1)
        if pubs: return pubs
    except Exception:
        pass
    # Classic GPA fallback
    try:
        cfg = {"encoding":"base64","commitment":"confirmed","dataSlice":{"offset":0,"length":8}}
        arr = _rpc_call_json(rpc, "getProgramAccounts", [program, cfg])
        for a in (arr or []):
            d = a.get("account",{}).get("data")
            b64 = d[0] if isinstance(d, list) and d else (d if isinstance(d, str) else None)
            if b64 == disc_b64:
                pub = a.get("pubkey")
                if pub and pub not in pubs: pubs.append(pub)
    except Exception:
        pass
    return pubs

def _find_store_account(rpc: str, program: str) -> Optional[str]:
    pubs = _find_accounts_by_disc(rpc, program, "Store", page_limit=1000, max_pages=20)
    return pubs[0] if pubs else None

def _list_markets(rpc: str, program: str, limit: int = 100) -> List[str]:
    pubs = _find_accounts_by_disc(rpc, program, "Market", page_limit=1000, max_pages=20)
    out, seen = [], set()
    for p in pubs:
        if p not in seen:
            out.append(p); seen.add(p)
        if len(out) >= limit: break
    return out

def _list_positions_for_owner(rpc: str, program: str, owner_b58: str, owner_off: int, limit: int) -> List[str]:
    cfg = {"encoding":"base64","commitment":"confirmed","limit":limit,"page":1,
           "filters":[{"memcmp":{"offset":int(owner_off),"bytes":owner_b58}}]}
    res, err = _rpc_call_json_safe(rpc, "getProgramAccounts", [program, cfg], timeout=8)
    if err: return []
    arr = res or []
    return [a.get("pubkey") for a in arr]

# Validated (Position discriminator)
_POSITION_DISC_B64 = _anchor_disc_b64("Position")
_ORDER_DISC_B64    = _anchor_disc_b64("Order")

def _account_has_disc(sess: "Session", pubkey: str, disc_b64: str) -> bool:
    res, err = _rpc_call_json_safe(sess.rpc_http, "getAccountInfo", [pubkey, {"encoding":"base64"}], timeout=6)
    if err or not res or not res.get("value"): return False
    data = res["value"].get("data")
    b64 = data[0] if isinstance(data, list) and data else data if isinstance(data, str) else None
    if not b64: return False
    try:
        raw = base64.b64decode(b64)
        return base64.b64encode(raw[:8]).decode() == disc_b64
    except Exception:
        return False

def _list_positions_valid(sess: "Session", limit: int = 200) -> List[str]:
    pks = _list_positions_for_owner(sess.rpc_http, sess.store_pid, sess.signer_pubkey or "", sess.owner_offset, limit)
    seen, out = set(), []
    for pk in pks:
        if pk in seen: continue
        if _account_has_disc(sess, pk, _POSITION_DISC_B64):
            out.append(pk); seen.add(pk)
    return out

def _list_orders_for_position(sess: "Session", position_b58: str, limit_per_offset: int = 200) -> list[str]:
    """Find Order accounts that reference the given position pubkey by memcmp
       at multiple common offsets, and confirm with Order discriminator."""
    if not _is_base58(position_b58): return []
    offsets_guess = [8, 24, 32, 40, 48, 56, 64, 72, 80, 96, 112, 128]
    seen, out = set(), []
    for off in offsets_guess:
        cfg_v2 = {
            "encoding": "base64",
            "commitment": "confirmed",
            "limit": limit_per_offset,
            "page": 1,
            "filters": [ { "memcmp": { "offset": int(off), "bytes": position_b58 } } ],
            "dataSlice": { "offset": 0, "length": 8 }
        }
        res, err = _rpc_call_json_safe(sess.rpc_http, "getProgramAccountsV2", [sess.store_pid, cfg_v2], timeout=8)
        accts = []
        if not err and res:
            if isinstance(res, list): accts = res
            elif isinstance(res, dict): accts = res.get("value") or res.get("accounts") or []
        else:
            cfg = {"encoding":"base64","commitment":"confirmed","limit":limit_per_offset,"page":1,
                   "filters":[{"memcmp":{"offset": int(off), "bytes": position_b58 }}], "dataSlice":{"offset":0,"length":8}}
            res2, err2 = _rpc_call_json_safe(sess.rpc_http, "getProgramAccounts", [sess.store_pid, cfg], timeout=8)
            accts = res2 or []
        for a in accts:
            pk = a.get("pubkey")
            if not pk or pk in seen: continue
            if _account_has_disc(sess, pk, _ORDER_DISC_B64):
                out.append(pk); seen.add(pk)
    return out

# ------------ Skeleton writer ------------
def _write_manifest_order_skeleton(sess: "Session") -> str:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    path = OUTBOX_DIR / f"{ts}_create_order_v2.json"
    jcfg = load_json(DEFAULT_JSON)
    man = {
        "instruction": "create_order_v2",
        "accounts": [
            {"name":"authority",    "isMut": True,  "isSigner": True,  "pubkey": sess.signer_pubkey or ""},
            {"name":"store",        "isMut": False, "isSigner": False, "pubkey": jcfg.get("store_account","")},
            {"name":"position",     "isMut": True,  "isSigner": False, "pubkey": jcfg.get("default_position","")},
            {"name":"order",        "isMut": True,  "isSigner": False, "pubkey": ""},
            {"name":"market",       "isMut": False, "isSigner": False, "pubkey": jcfg.get("default_market","")},
            {"name":"tokenProgram", "isMut": False, "isSigner": False, "pubkey": SPL_TOKEN},
        ],
        "args": {
            "sizeDelta": 0,
            "collateralDelta": 0,
            "orderKind": 0,
            "priceType": 0,
            "triggerPriceX32": "0",
            "slippageBps": 0,
            "ttlSeconds": 0,
        }
    }
    path.write_text(json.dumps(man, indent=2), encoding="utf-8")
    return str(path)

def _latest_order_manifest() -> Optional[str]:
    try:
        return max(glob.glob(r"C:\sonic7\outbox\*_create_order_v2.json"), key=lambda p: os.path.getmtime(p))
    except Exception:
        return None

# ------------ PDA Recipe Helpers ------------
def _load_recipe() -> Optional[List[dict]]:
    j = load_json(DEFAULT_JSON)
    r = j.get("order_pda_recipe")
    return r if isinstance(r, list) else None

def _save_recipe(recipe: List[dict]) -> None:
    j = load_json(DEFAULT_JSON)
    j["order_pda_recipe"] = recipe
    save_json(j, DEFAULT_JSON)

def _seeds_from_recipe(recipe: List[dict], man: dict, sess: "Session") -> Tuple[List[bytes], List[str]]:
    seeds: List[bytes] = []; dbg: List[str] = []
    for it in recipe:
        if "literal" in it:
            s = str(it["literal"]).encode("utf-8")
            seeds.append(s); dbg.append(f"literal:{s.decode()}")
        elif "pubkey" in it:
            name = str(it["pubkey"])
            val = acc_get(man, name) or ""
            if not val:
                if name=="position":   val = load_json(DEFAULT_JSON).get("default_position","")
                elif name=="market":   val = load_json(DEFAULT_JSON).get("default_market","")
                elif name=="authority":val = load_json(DEFAULT_JSON).get("signer_pubkey","")
                elif name=="store":    val = load_json(DEFAULT_JSON).get("store_account","")
            if not _is_base58(val): raise RuntimeError(f"Seed '{name}' missing/not base58.")
            if not HAVE_SOLDERS:   raise RuntimeError("solders not installed (`pip install solders`).")
            seeds.append(Pubkey.from_string(val).to_bytes()); dbg.append(f"pubkey:{name}={val}")
        elif "u8" in it:
            n = int(it["u8"]);  seeds.append(n.to_bytes(1,"little")); dbg.append(f"u8:{n}")
        elif "u32" in it:
            n = int(it["u32"]); seeds.append(n.to_bytes(4,"little")); dbg.append(f"u32:{n}")
        elif "u64" in it:
            n = int(it["u64"]); seeds.append(n.to_bytes(8,"little")); dbg.append(f"u64:{n}")
        else:
            raise RuntimeError(f"Unknown recipe entry: {it}")
    return seeds, dbg

def _derive_order_pda(sess: "Session", man: dict) -> Tuple[Optional[str], str]:
    if not HAVE_SOLDERS:
        return None, "solders not installed. Install:  pip install solders"
    recipe = _load_recipe()
    if not recipe:
        return None, ("No order_pda_recipe configured. Example:\n"
                      '[{"literal":"order"},{"pubkey":"position"},{"pubkey":"market"}]')
    try:
        seeds, dbg = _seeds_from_recipe(recipe, man, sess)
        program = Pubkey.from_string(sess.store_pid)
        pda, bump = Pubkey.find_program_address(seeds, program)
        pda_s = str(pda)
        info, err = _rpc_call_json_safe(sess.rpc_http, "getAccountInfo", [pda_s, {"encoding":"base64"}], timeout=6)
        if err:
            return pda_s, f"Derived PDA {pda_s} (bump={bump}); owner unknown ({err})"
        owner = ((info or {}).get("value") or {}).get("owner")
        if owner == sess.store_pid:
            return pda_s, f"{CHECK} PDA {pda_s} (bump={bump}) owner=store_program"
        return pda_s, f"{WARN} PDA {pda_s} (bump={bump}) owner={owner or '(none)'} — verify recipe"
    except Exception as e:
        return None, f"Derivation failed: {e}"

def _auto_derive_order_pda(sess: "Session", man: dict) -> Tuple[Optional[str], str]:
    if not HAVE_SOLDERS:
        return None, "solders not installed. Install:  pip install solders"

    position = acc_get(man, "position") or load_json(DEFAULT_JSON).get("default_position","")
    market   = acc_get(man, "market")   or load_json(DEFAULT_JSON).get("default_market","")
    auth     = acc_get(man, "authority") or load_json(DEFAULT_JSON).get("signer_pubkey","")
    store    = acc_get(man, "store") or load_json(DEFAULT_JSON).get("store_account","")

    for need, val in (("position",position),("market",market),("store",store),("authority",auth)):
        if need in ("position","market") and not _is_base58(val):
            return None, f"Missing {need}. Use wizard steps 2/3/4 first."

    candidates: List[List[dict]] = [
        [{"literal":"order"},{"pubkey":"position"},{"pubkey":"market"}],
        [{"literal":"order"},{"pubkey":"market"},{"pubkey":"position"}],
        [{"literal":"order"},{"pubkey":"position"}],
        [{"literal":"order"},{"pubkey":"market"}],
        [{"literal":"order"},{"pubkey":"authority"},{"pubkey":"market"}],
        [{"literal":"order"},{"pubkey":"authority"},{"pubkey":"position"}],
    ]

    program = Pubkey.from_string(sess.store_pid)
    valid: List[str] = []
    tried: List[str] = []

    for recipe in candidates:
        try:
            seeds, _ = _seeds_from_recipe(recipe, man, sess)
            pda, bump = Pubkey.find_program_address(seeds, program)
            pda_s = str(pda)
            tried.append(pda_s)
            info, err = _rpc_call_json_safe(sess.rpc_http, "getAccountInfo", [pda_s, {"encoding":"base64"}], timeout=6)
            if err or not info or not info.get("value"):
                continue
            owner = info["value"].get("owner")
            if owner == sess.store_pid:
                valid.append(pda_s)
        except Exception:
            continue

    if len(valid) == 1:
        return valid[0], f"{CHECK} Auto-derived Order PDA: {valid[0]}"
    elif len(valid) > 1:
        return None, f"{WARN} Multiple candidate PDAs found:\n" + "\n".join([f"  • {x}" for x in valid])
    else:
        return None, f"{WARN} No valid Order PDA found via auto-recipes.\nTried:\n" + ("\n".join([f"  • {x}" for x in tried]) if tried else "  • (none)")

# ------------ Clear/Refresh helpers ------------
def _clear_saved_defaults():
    j = load_json(DEFAULT_JSON)
    j["default_position"] = ""
    j["default_market"]   = ""
    save_json(j, DEFAULT_JSON)

def _scrub_manifest_pos_order():
    mf = _latest_order_manifest()
    if not mf:
        return None, "No order manifest found."
    try:
        man = json.loads(Path(mf).read_text(encoding="utf-8"))
        ensure_accounts_list(man)
        acc_set(man, "position", "")
        acc_set(man, "order", "")
        Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
        return mf, "Scrubbed 'position' and 'order' in manifest."
    except Exception as e:
        return None, f"Failed to scrub manifest: {e}"

# ------------ Session ------------
class Session:
    def __init__(self):
        j = load_json(DEFAULT_JSON)
        self.rpc_http: str = j.get("sol_rpc") or ""
        self.store_pid: str = j.get("store_program_id") or STORE_PROG_ID
        self.signer_file: Path = Path(j.get("signer_file") or r"C:\sonic7\signer.txt")
        if not self.signer_file.exists():
            for p in [Path.cwd()/"signer.txt", Path.cwd()/"signer", Path(r"C:\sonic7\signer")]:
                if p.exists(): self.signer_file = p; break
        self.signer_pubkey: Optional[str] = j.get("signer_pubkey") or derive_pub_from_signer_file(str(self.signer_file))
        self.limit: int = int(j.get("limit") or 100)
        self.page: int = int(j.get("page") or 1)
        self.owner_offset: int = int(j.get("owner_offset") or 24)
        self.data_size: Optional[int] = (int(j["data_size"]) if ("data_size" in j and str(j["data_size"]).isdigit()) else None)
        self.prefer_v2: bool = bool(j.get("prefer_v2", True))
        self.store_account: Optional[str]    = j.get("store_account") or ""
        self.default_position: Optional[str] = j.get("default_position") or ""
        self.default_market: Optional[str]   = j.get("default_market") or ""

    def persist(self) -> None:
        cur = load_json(DEFAULT_JSON)
        out = {
            "sol_rpc": self.rpc_http,
            "store_program_id": self.store_pid,
            "signer_file": str(self.signer_file),
            "signer_pubkey": self.signer_pubkey or "",
            "limit": self.limit,
            "page": self.page,
            "owner_offset": self.owner_offset,
            "data_size": self.data_size if self.data_size else 0,
            "prefer_v2": self.prefer_v2,
            "store_account": self.store_account or "",
            "default_position": self.default_position or "",
            "default_market": self.default_market or "",
            "order_pda_recipe": cur.get("order_pda_recipe", []),
            "order_defaults":   cur.get("order_defaults", {}),
            "order_kind_map":   cur.get("order_kind_map", {}),
            "price_type_map":   cur.get("price_type_map", {}),
        }
        save_json(out, DEFAULT_JSON)

    def header(self) -> None:
        print("=" * 72)
        print("         🌊 GMX-Solana Interactive Console (Option A + builders)         ")
        print("=" * 72)
        print(f" 🩺 RPC        : {self.rpc_http or '(not set)'}")
        print(f" 🏦 Store PID  : {self.store_pid or '(not set)'}")
        print(f" 📝 Signer File: {self.signer_file}")
        print(f" 👤 Signer Pub : {self.signer_pubkey or '(not derived)'}")
        ds = self.data_size if self.data_size else "(none)"
        v2 = "on" if self.prefer_v2 else "off"
        print(f" 🧭 OwnerOff   : {self.owner_offset}   📦 limit={self.limit}  🧺 page={self.page}")
        print(f" 🔎 Filters    : dataSize={ds}  V2={v2}")
        print(f" ⚙️  Config JSON: {DEFAULT_JSON}")
        print(f" 📂 Outbox     : {OUTBOX_DIR}")
        if self.store_account:    print(f" 🛰 Store acct : {self.store_account}")
        if self.default_position: print(f" 📌 Def. pos   : {self.default_position}")
        if self.default_market:   print(f" 🧭 Def. market: {self.default_market}")
        print("-" * 72)

# ------------ Status (for [34] and wizard banner) ------------
REQ_ACCOUNTS = ["authority","store","position","market","order","tokenProgram"]
REQ_ARGS     = ["sizeDelta","collateralDelta","orderKind","priceType","triggerPriceX32","slippageBps","ttlSeconds"]

def _status_check(sess: Session) -> Dict[str, Any]:
    s: Dict[str, Any] = {}
    s["cfg_signer_pubkey"] = bool(sess.signer_pubkey)
    s["cfg_store_account"] = bool(sess.store_account)
    mf = _latest_order_manifest()
    s["manifest_exists"]   = bool(mf)
    s["manifest_path"]     = mf or ""
    man = None
    if mf:
        try:
            man = json.loads(Path(mf).read_text(encoding="utf-8"))
            ensure_accounts_list(man)
        except Exception:
            man = None
    for k in REQ_ACCOUNTS:
        s[f"acc_{k}"] = bool(man and acc_get(man, k))
    args_ok = bool(man and isinstance(man.get("args"), dict) and set(man["args"].keys()) >= set(REQ_ARGS))
    s["args_complete"] = args_ok
    all_accounts_ok = all(s[f"acc_{k}"] for k in REQ_ACCOUNTS)
    s["ready"] = s["cfg_signer_pubkey"] and s["cfg_store_account"] and s["manifest_exists"] and all_accounts_ok and s["args_complete"]
    return s

def _print_status(sess: Session) -> None:
    s = _status_check(sess)
    def mark(b): return CHECK if b else CROSS
    print("──────────────────────────────────────────────────────────────────────")
    print("  📊 Order Status")
    print("──────────────────────────────────────────────────────────────────────")
    print(f"  {mark(s['cfg_signer_pubkey'])} RPC & Signer pubkey")
    print(f"  {mark(s['cfg_store_account'])} Store account saved")
    print(f"  {mark(s['manifest_exists'])} Manifest exists   {INFO} {s['manifest_path'] or '(none)'}")
    print("  Accounts  :", " ".join([f"{mark(s[f'acc_{k}'])} {k}" for k in REQ_ACCOUNTS]))
    print(f"  Args      : {mark(s['args_complete'])} {', '.join(REQ_ARGS)}")
    print("──────────────────────────────────────────────────────────────────────")
    print("  " + (f"{ROCKET} READY to simulate/send" if s["ready"] else f"{WARN} Not ready — fill red items"))
    print("──────────────────────────────────────────────────────────────────────")

# ------------ Pretty “Order Details” ------------
def _load_latest_manifest() -> tuple[Optional[str], Optional[dict]]:
    mf = _latest_order_manifest()
    if not mf: return None, None
    try:
        man = json.loads(Path(mf).read_text(encoding="utf-8"))
        ensure_accounts_list(man)
        return mf, man
    except Exception:
        return mf, None

def _print_order_details(man: Optional[dict]):
    if not man:
        print("  🧾 Order Details: (none)")
        return
    accs = {k: acc_get(man, k) for k in ("authority","store","position","market","order","tokenProgram")}
    def mk(v): return CHECK if _is_base58(v) else CROSS
    print("  🧾 Order Details")
    print("  ──────────────────────────────────────────")
    print(f"  {mk(accs['authority'])} 👤 authority     : {accs['authority'] or '(unset)'}")
    print(f"  {mk(accs['store'])} 🛰 store         : {accs['store'] or '(unset)'}")
    print(f"  {mk(accs['position'])} 🎯 position      : {accs['position'] or '(unset)'}")
    print(f"  {mk(accs['market'])} 🧭 market        : {accs['market'] or '(unset)'}")
    print(f"  {mk(accs['order'])} 🔑 order PDA     : {accs['order'] or '(unset)'}")
    print(f"  {mk(accs['tokenProgram'])} 🧪 tokenProgram : {accs['tokenProgram'] or '(unset)'}")
    args = man.get("args", {})
    def show_arg(key, icon, label):
        v = args.get(key, None); ok = v not in (None, "", [])
        print(f"  {'✅' if ok else '❌'} {icon} {label:<20}: {v if ok else '(unset)'}")
    print("  ──────────────────────────────────────────")
    show_arg("sizeDelta",       "📏", "Position size change")
    show_arg("collateralDelta", "💰", "Collateral change")
    show_arg("orderKind",       "🎛️", "Order kind (enum)")
    show_arg("priceType",       "🏷", "Price type (enum)")
    show_arg("triggerPriceX32", "🎯", "Trigger price x32")
    show_arg("slippageBps",     "🧪", "Allowed slippage (bps)")
    show_arg("ttlSeconds",      "⏱", "Time-to-live (s)")
    print("  ──────────────────────────────────────────")

# ------------ Main Menu ------------
def run_menu():
    sess = Session()
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        sess.header()
        print("  [1]  🩺 RPC health")
        print("  [2]  🏦 Set Store Program ID")
        print("  [3]  ✍️  Set Signer file path (re-derive pubkey)")
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
        choice = input("Select: ").strip()

        try:
            if choice == "0":
                print("Bye."); return

            elif choice == "1":
                if not sess.rpc_http: print("⚠️  RPC not set in config."); input("<enter>"); continue
                slot, err = _rpc_call_json_safe(sess.rpc_http, "getSlot", [], timeout=6)
                print(pretty({"health": "ok" if not err else "error", "slot": slot, "err": err})); input("<enter>")

            elif choice == "2":
                pid = input(f"Store Program ID [{sess.store_pid}]: ").strip()
                if pid: sess.store_pid = pid; sess.persist()
                input("<enter>")

            elif choice == "3":
                p = input(f"Signer file path [{sess.signer_file}]: ").strip() or str(sess.signer_file)
                sess.signer_file = Path(p)
                sess.signer_pubkey = derive_pub_from_signer_file(str(sess.signer_file)) or sess.signer_pubkey
                print("Signer pubkey:", sess.signer_pubkey or "(not derived)"); sess.persist(); input("<enter>")

            elif choice == "4":
                cfg = {"encoding":"base64","commitment":"confirmed","limit":10,"page":1}
                res, err = _rpc_call_json_safe(sess.rpc_http, "getProgramAccountsV2", [sess.store_pid, cfg], timeout=8)
                accts = (res.get("value") or res.get("accounts")) if isinstance(res, dict) else (res if isinstance(res, list) else [])
                sample = [a.get("pubkey") for a in (accts or [])[:10]]
                print(pretty({"program":sess.store_pid, "sample":sample, "count_page": len(accts or []), "err": err})); input("<enter>")

            elif choice == "5":
                if not (sess.rpc_http and sess.signer_pubkey): print("⚠️  Set RPC + signer pubkey."); input("<enter>"); continue
                pks = _list_positions_for_owner(sess.rpc_http, sess.store_pid, sess.signer_pubkey, sess.owner_offset, sess.limit)
                print(pretty({"matched_account_count": len(pks), "sample_pubkeys": pks[:10]})); input("<enter>")

            elif choice == "6":
                pk = input("Enter pubkey: ").strip()
                if not pk: input("<enter>"); continue
                res, err = _rpc_call_json_safe(sess.rpc_http, "getAccountInfo", [pk, {"encoding":"base64"}], timeout=8)
                print(pretty(res if not err else {"error": err})); input("<enter>")

            elif choice == "7":
                try:
                    sess.limit = int(input(f"limit [{sess.limit}]: ").strip() or sess.limit)
                    sess.page  = int(input(f"page  [{sess.page }]: ").strip() or sess.page)
                    sess.owner_offset = int(input(f"owner offset [{sess.owner_offset}]: ").strip() or sess.owner_offset)
                    sess.persist()
                except Exception as e:
                    print("bad input:", e)
                input("<enter>")

            elif choice == "8":
                offs = [0,8,16,24,32,40,48,56,64,72,80,96,112,128]
                out = []
                for off in offs:
                    cfg = {"encoding":"base64","commitment":"confirmed","limit":sess.limit,"page":1,
                           "filters":[{"memcmp":{"offset":off,"bytes":sess.signer_pubkey}}]}
                    res, err = _rpc_call_json_safe(sess.rpc_http, "getProgramAccounts", [sess.store_pid, cfg], timeout=6)
                    out.append((off, -1 if err else len(res or [])))
                print(pretty({"sweep": out})); input("<enter>")

            elif choice in ("20","21","22"):
                ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
                ins = {"20":"prepare_position","21":"create_deposit","22":"create_withdrawal"}[choice]
                path = OUTBOX_DIR / f"{ts}_{ins}.json"
                man = {"instruction": ins, "accounts": [], "args": {}}
                path.write_text(json.dumps(man, indent=2), encoding="utf-8")
                print(f"{ins} manifest written: {path}"); input("<enter>")

            elif choice == "23":
                mf = _write_manifest_order_skeleton(sess)
                print(f"✅ Manifest created: {mf}"); input("<enter>")

            elif choice == "24":
                print(str(OUTBOX_DIR.resolve())); input("<enter>")

            elif choice == "25":
                print("⏳ Scanning for Store…")
                store = _find_store_account(sess.rpc_http, sess.store_pid)
                if store:
                    j=load_json(DEFAULT_JSON); j["store_account"]=store; save_json(j, DEFAULT_JSON)
                    sess.store_account = store; sess.persist()
                    print("✅ store_account:", store)
                else:
                    print("⚠️  Not found/timeout.")
                input("<enter>")

            elif choice == "26":
                p = input("Paste POSITION pubkey: ").strip()
                if p and _is_base58(p):
                    j=load_json(DEFAULT_JSON); j["default_position"]=p; save_json(j, DEFAULT_JSON)
                    sess.default_position = p; sess.persist(); print("✅ default_position saved.")
                else: print("⚠️  Not base58.")
                input("<enter>")

            elif choice == "27":
                m = input("Paste MARKET pubkey: ").strip()
                if m and _is_base58(m):
                    j=load_json(DEFAULT_JSON); j["default_market"]=m; save_json(j, DEFAULT_JSON)
                    sess.default_market = m; sess.persist(); print("✅ default_market saved.")
                else: print("⚠️  Not base58.")
                input("<enter>")

            elif choice == "28":
                mf = _latest_order_manifest()
                if not mf: print("No order manifest. Run [23] first."); input("<enter>"); continue
                man = json.loads(Path(mf).read_text(encoding="utf-8"))
                ensure_accounts_list(man)
                changed=[]
                if sess.signer_pubkey and not acc_get(man,"authority"):  acc_set(man,"authority", sess.signer_pubkey, mut=True, signer=True); changed.append("authority")
                jcfg = load_json(DEFAULT_JSON)
                if jcfg.get("store_account") and not acc_get(man,"store"):
                    acc_set(man,"store", jcfg["store_account"], mut=False); changed.append("store")
                if not acc_get(man,"tokenProgram"): acc_set(man,"tokenProgram", SPL_TOKEN); changed.append("tokenProgram")
                if jcfg.get("default_position") and not acc_get(man,"position"):
                    acc_set(man,"position", jcfg["default_position"], mut=True); changed.append("position")
                if jcfg.get("default_market") and not acc_get(man,"market"):
                    acc_set(man,"market",  jcfg["default_market"], mut=False); changed.append("market")
                Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                print(f"✅ Prefilled {mf} 🔧 {', '.join(changed) if changed else '(nothing)'}"); input("<enter>")

            elif choice == "29":
                j = load_json(DEFAULT_JSON)
                print(pretty({
                    "store_account": j.get("store_account","(not set)"),
                    "default_position": j.get("default_position","(not set)"),
                    "default_market": j.get("default_market","(not set)"),
                    "order_pda_recipe": j.get("order_pda_recipe", []),
                    "order_defaults": j.get("order_defaults", {}),
                    "order_kind_map": j.get("order_kind_map", {}),
                    "price_type_map": j.get("price_type_map", {}),
                })); input("<enter>")

            elif choice == "30":
                if not (sess.rpc_http and sess.signer_pubkey): print("⚠️ Need RPC + signer pubkey."); input("<enter>"); continue
                print("⏳ Scanning VALID positions…")
                picks = _list_positions_valid(sess, limit=200)
                if not picks: print("⚠️ No valid positions. Try Sweep [8] then adjust [7]."); input("<enter>"); continue
                for i,p in enumerate(picks,1): print(f"  [{i}] {p}")
                sel = input("Pick #: ").strip()
                if not (sel.isdigit() and 1 <= int(sel) <= len(picks)): print("Canceled."); input("<enter>"); continue
                j=load_json(DEFAULT_JSON); j["default_position"]=picks[int(sel)-1]; save_json(j, DEFAULT_JSON)
                sess.default_position = picks[int(sel)-1]; sess.persist()
                print("✅ default_position saved:", sess.default_position); input("<enter>")

            elif choice == "31":
                print("⏳ Listing markets…")
                markets = _list_markets(sess.rpc_http, sess.store_pid, limit=100)
                if not markets: print("⚠️ No markets."); input("<enter>"); continue
                for i,m in enumerate(markets,1): print(f"  [{i}] {m}")
                sel = input("Pick #: ").strip()
                if not (sel.isdigit() and 1 <= int(sel) <= len(markets)): print("Canceled."); input("<enter>"); continue
                j=load_json(DEFAULT_JSON); j["default_market"]=markets[int(sel)-1]; save_json(j, DEFAULT_JSON)
                sess.default_market = markets[int(sel)-1]; sess.persist()
                print("✅ default_market saved:", sess.default_market); input("<enter>")

            elif choice == "32":
                mf = _latest_order_manifest() or _write_manifest_order_skeleton(sess)
                man = json.loads(Path(mf).read_text(encoding="utf-8"))
                ensure_accounts_list(man)
                jcfg = load_json(DEFAULT_JSON)
                if sess.signer_pubkey and not acc_get(man,"authority"):  acc_set(man,"authority", sess.signer_pubkey, mut=True, signer=True)
                if jcfg.get("store_account") and not acc_get(man,"store"): acc_set(man,"store", jcfg["store_account"])
                if not acc_get(man,"tokenProgram"): acc_set(man,"tokenProgram", SPL_TOKEN)
                if not acc_get(man,"position"):
                    picks = _list_positions_valid(sess, limit=200)
                    if picks:
                        for i,p in enumerate(picks,1): print(f"  [{i}] {p}")
                        sel = input("Pick POSITION #: ").strip()
                        if sel.isdigit() and 1 <= int(sel) <= len(picks): acc_set(man,"position", picks[int(sel)-1], mut=True)
                if not acc_get(man,"market"):
                    markets = _list_markets(sess.rpc_http, sess.store_pid, limit=100)
                    if markets:
                        for i,m in enumerate(markets,1): print(f"  [{i}] {m}")
                        sel = input("Pick MARKET #: ").strip()
                        if sel.isdigit() and 1 <= int(sel) <= len(markets): acc_set(man,"market", markets[int(sel)-1])
                Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                print("✅ Guided prefill done.\nManifest:", mf); input("<enter>")

            elif choice == "33":
                order_wizard_submenu(sess)

            elif choice == "34":
                _print_status(sess); input("<enter>")

            elif choice == "35":
                print("⏳ Refreshing positions/markets…")
                valid_pos = _list_positions_valid(sess, limit=200)
                mkts      = _list_markets(sess.rpc_http, sess.store_pid, limit=200)
                cleared = []
                if sess.default_position and sess.default_position not in valid_pos:
                    sess.default_position = ""; cleared.append("default_position")
                if sess.default_market and sess.default_market not in mkts:
                    sess.default_market = ""; cleared.append("default_market")
                sess.persist()
                print(f"✅ Positions: {len(valid_pos)}  Markets: {len(mkts)}")
                print(("🧹 Cleared: " + ", ".join(cleared)) if cleared else "🟢 Defaults look good.")
                input("<enter>")

            elif choice == "36":
                _clear_saved_defaults()
                sess.default_position = ""
                sess.default_market   = ""
                sess.persist()
                print("🧹 Cleared saved defaults (position/market).")
                input("<enter>")

            else:
                print("Unknown selection."); input("<enter>")

        except KeyboardInterrupt:
            print("\nBye."); return
        except Exception as e:
            print("Unhandled error:", e); input("<enter>")

# ------------ Order Wizard ------------
def order_wizard_submenu(sess: Session) -> None:
    while True:
        os.system('cls' if os.name=='nt' else 'clear')
        print("──────────────────────────────────────────────────────────────────────")
        print("  🧩  Order Wizard")
        print("──────────────────────────────────────────────────────────────────────")
        cfg = load_json(DEFAULT_JSON)
        print(f"  🛰 store_account : {cfg.get('store_account','(not set)')}")
        print(f"  📌 def_position  : {cfg.get('default_position','(not set)')}")
        print(f"  🧭 def_market    : {cfg.get('default_market','(not set)')}")
        _print_status(sess)
        mf, man = _load_latest_manifest()
        _print_order_details(man)
        print("  [1]  🔍 Detect & save Store")
        print("  [2]  📋 Pick Position (save default)")
        print("  [3]  🗺 Pick Market (save default)")
        print("  [4]  🧾 Prefill latest order manifest")
        print("  [5]  🔑 Derive Order PDA (recipe/auto)")
        print("  [6]  ✍️  Paste Order PDA (manual)")
        print("  [7]  ⚙️  Edit Args (typed values)")
        print("  [8]  📂 Show latest manifest path")
        print("  [9]  ▶️  Print simulate command")
        print("  [10] 🔎 Find Order PDA (scan & pick)")
        print("  [11] 🧹 Clear manifest (order/position)")
        print("  [0]  ↩️  Back")
        sub = input("Select: ").strip()

        try:
            if sub == "0":
                return

            elif sub == "1":
                print("⏳ Scanning for Store…")
                store = _find_store_account(sess.rpc_http, sess.store_pid)
                if store:
                    j=load_json(DEFAULT_JSON); j["store_account"]=store; save_json(j, DEFAULT_JSON)
                    sess.store_account = store; sess.persist()
                    print("✅ store_account:", store)
                else:
                    print("⚠️  Could not find Store.")
                input("<enter>")

            elif sub == "2":
                print("⏳ Scanning VALID positions…")
                picks = _list_positions_valid(sess, limit=200)
                if not picks:
                    print("⚠️  No positions; try Sweep Offsets in main menu."); input("<enter>"); continue
                for i,p in enumerate(picks,1): print(f"  [{i}] {p}")
                sel = input("Pick #: ").strip()
                if not (sel.isdigit() and 1 <= int(sel) <= len(picks)): print("Canceled."); input("<enter>"); continue
                j=load_json(DEFAULT_JSON); j["default_position"]=picks[int(sel)-1]; save_json(j, DEFAULT_JSON)
                sess.default_position = picks[int(sel)-1]; sess.persist()
                print("✅ default_position:", sess.default_position); input("<enter>")

            elif sub == "3":
                print("⏳ Listing markets…")
                markets = _list_markets(sess.rpc_http, sess.store_pid, limit=100)
                if not markets: print("⚠️  No markets."); input("<enter>"); continue
                for i,m in enumerate(markets,1): print(f"  [{i}] {m}")
                sel = input("Pick #: ").strip()
                if not (sel.isdigit() and 1 <= int(sel) <= len(markets)): print("Canceled."); input("<enter>"); continue
                j=load_json(DEFAULT_JSON); j["default_market"]=markets[int(sel)-1]; save_json(j, DEFAULT_JSON)
                sess.default_market = markets[int(sel)-1]; sess.persist()
                print("✅ default_market:", sess.default_market); input("<enter>")

            elif sub == "4":
                mf = _latest_order_manifest() or _write_manifest_order_skeleton(sess)
                man = json.loads(Path(mf).read_text(encoding="utf-8"))
                ensure_accounts_list(man)
                changed=[]
                if sess.signer_pubkey and not acc_get(man,"authority"):  acc_set(man,"authority", sess.signer_pubkey, mut=True, signer=True); changed.append("authority")
                if cfg.get("store_account") and not acc_get(man,"store"):  acc_set(man,"store", cfg["store_account"]); changed.append("store")
                if not acc_get(man,"tokenProgram"): acc_set(man,"tokenProgram", SPL_TOKEN); changed.append("tokenProgram")
                if cfg.get("default_position") and not acc_get(man,"position"): acc_set(man,"position", cfg["default_position"], mut=True); changed.append("position")
                if cfg.get("default_market") and not acc_get(man,"market"):     acc_set(man,"market",  cfg["default_market"]); changed.append("market")
                Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                print("✅ Prefilled:", mf, "  🔧", ", ".join(changed) if changed else "(nothing)"); input("<enter>")

            elif sub == "5":
                mf = _latest_order_manifest() or _write_manifest_order_skeleton(sess)
                man = json.loads(Path(mf).read_text(encoding="utf-8"))
                ensure_accounts_list(man)

                recipe = _load_recipe()
                if recipe:
                    if not HAVE_SOLDERS:
                        print(f"{CROSS} 'solders' not installed. pip install solders")
                        print("   Or use step [6] to paste PDA manually.")
                        input("<enter>"); continue
                    pda, msg = _derive_order_pda(sess, man)
                    print(msg)
                    if pda:
                        acc_set(man,"order", pda, mut=True)
                        Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                        print("✅ Wrote 'order' into manifest.")
                    input("<enter>")
                else:
                    print("\nNo order_pda_recipe in config.")
                    print("1) Auto-derive (try common seeds)")
                    print('2) Paste a recipe JSON (e.g. [{"literal":"order"},{"pubkey":"position"},{"pubkey":"market"}])')
                    print("0) Cancel")
                    pick = input("Choose [1/2/0]: ").strip()
                    if pick == "1":
                        pda, msg = _auto_derive_order_pda(sess, man)
                        print(msg)
                        if pda:
                            acc_set(man,"order", pda, mut=True)
                            Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                            print("✅ Wrote 'order' into manifest.")
                        else:
                            # Offer scan fallback
                            if input("Run Order PDA scan for this position now? (Y/n): ").strip().lower() in ("","y","yes"):
                                pos = acc_get(man,"position") or load_json(DEFAULT_JSON).get("default_position","")
                                found = _list_orders_for_position(sess, pos)
                                if found:
                                    for i,pk in enumerate(found,1): print(f"  [{i}] {pk}")
                                    sel = input("Pick #: ").strip()
                                    if sel.isdigit() and 1 <= int(sel) <= len(found):
                                        acc_set(man,"order", found[int(sel)-1], mut=True)
                                        Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                                        print("✅ Wrote 'order' into manifest.")
                                else:
                                    print("⚠️  Scanner found no Order accounts for this position.")
                        input("<enter>")
                    elif pick == "2":
                        raw = input("Paste recipe JSON (or Enter to cancel): ").strip()
                        if raw:
                            try:
                                rec = json.loads(raw); _save_recipe(rec); print("✅ Recipe saved. Re-run step [5].")
                            except Exception as e:
                                print("Bad JSON:", e)
                        input("<enter>")
                    else:
                        pass

            elif sub == "6":
                mf = _latest_order_manifest() or _write_manifest_order_skeleton(sess)
                man = json.loads(Path(mf).read_text(encoding="utf-8"))
                ensure_accounts_list(man)
                op = input("Paste ORDER PDA pubkey: ").strip()
                if not _is_base58(op): print("⚠️  Not base58."); input("<enter>"); continue
                acc_set(man,"order", op, mut=True); Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                print("✅ Set 'order' in manifest."); input("<enter>")

            elif sub == "7":
                mf = _latest_order_manifest() or _write_manifest_order_skeleton(sess)
                man = json.loads(Path(mf).read_text(encoding="utf-8"))
                if not isinstance(man.get("args"), dict): man["args"] = {}
                dfl = _cfg_defaults()
                maps = _cfg_maps()

                print("\n⚙️  Set order parameters (Enter = keep current/default)")
                print("   📏 sizeDelta: Position size change (u64). For withdraw-only, set 0.")
                print("   💰 collateralDelta: Collateral change (u64). Positive to add, per GMX semantics.")
                print("   🎛️ orderKind: Action enum. (use name or int)")
                if maps["orderKind"]:
                    print("      →", ", ".join([f"{n}({v})" for n,v in maps["orderKind"].items()]))
                print("   🏷 priceType: Pricing enum. (use name or int)")
                if maps["priceType"]:
                    print("      →", ", ".join([f"{n}({v})" for n,v in maps["priceType"].items()]))

                def ask_int(label, cur):
                    s = input(f"   {label} [{cur}]: ").strip()
                    if s == "": return cur
                    try: return int(s)
                    except: print("    → bad input, keeping current"); return cur

                def ask_enum(label, key, cur, emap):
                    s = input(f"   {label} (name or int) [{cur}]: ").strip()
                    if s == "": return cur
                    if s.isdigit(): return int(s)
                    v = emap.get(s.upper())
                    if v is None:
                        print("    → unknown name; keeping current")
                        return cur
                    return int(v)

                cur = man["args"]
                cur["sizeDelta"]        = ask_int("📏 sizeDelta (u64)",        int(cur.get("sizeDelta", 0)))
                cur["collateralDelta"]  = ask_int("💰 collateralDelta (u64)",  int(cur.get("collateralDelta", 0)))
                if maps["orderKind"]:
                    cur["orderKind"]    = ask_enum("🎛️ orderKind", "orderKind", int(cur.get("orderKind", 0)), maps["orderKind"])
                else:
                    cur["orderKind"]    = ask_int("🎛️ orderKind (u16)",        int(cur.get("orderKind", 0)))
                if maps["priceType"]:
                    cur["priceType"]    = ask_enum("🏷 priceType", "priceType", int(cur.get("priceType", 0)), maps["priceType"])
                else:
                    cur["priceType"]    = ask_int("🏷 priceType (u16)",        int(cur.get("priceType", 0)))
                tcur = str(cur.get("triggerPriceX32", "0"))
                tnew = input(f"   🎯 triggerPriceX32 (u128) [{tcur}]: ").strip()
                cur["triggerPriceX32"]  = tnew if tnew != "" else tcur
                cur["slippageBps"]      = ask_int("🧪 slippageBps (u16)",      int(cur.get("slippageBps", dfl["slippageBps"])))
                cur["ttlSeconds"]       = ask_int("⏱ ttlSeconds (u32)",        int(cur.get("ttlSeconds",  dfl["ttlSeconds"])))

                Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                print(f"✅ Args saved: {mf}")
                _print_order_details(man)
                input("<enter>")

            elif sub == "8":
                print(_latest_order_manifest() or "(no manifest)"); input("<enter>")

            elif sub == "9":
                mf = _latest_order_manifest()
                if not mf: print("ℹ️  Use [4] to create/prefill a manifest first."); input("<enter>"); continue
                print("\n▶️  Simulate (no send):")
                print(rf'python C:\sonic7\scripts\gmsol_build_and_send_v2.py send-manifest --rpc "{sess.rpc_http}" --program {sess.store_pid} --idl C:\sonic7\backend\core\gmsol_solana_core\idl\gmsol-store.json --idl C:\sonic7\backend\core\gmx_solana_core\idl\gmsol-store.json --signer-mnemonic-file C:\sonic7\signer.txt --manifest {mf}')
                print("Add --send when simulate is clean."); input("<enter>")

            elif sub == "10":
                # Order PDA Finder (scan & pick)
                mf = _latest_order_manifest() or _write_manifest_order_skeleton(sess)
                man = json.loads(Path(mf).read_text(encoding="utf-8"))
                ensure_accounts_list(man)
                pos = acc_get(man, "position") or load_json(DEFAULT_JSON).get("default_position","")
                if not _is_base58(pos):
                    print("⚠️  No position set. Use steps [2]/[4] first.")
                    input("<enter>"); continue
                print("⏳ Scanning for Order accounts that reference this position…")
                found = _list_orders_for_position(sess, pos, limit_per_offset=200)
                if not found:
                    print("⚠️  No Order accounts found for this position (or timeout).")
                    input("<enter>"); continue
                for i,pk in enumerate(found, 1):
                    print(f"  [{i}] {pk}")
                sel = input("Pick Order PDA #: ").strip()
                if not (sel.isdigit() and 1 <= int(sel) <= len(found)):
                    print("Canceled."); input("<enter>"); continue
                picked = found[int(sel)-1]
                acc_set(man, "order", picked, mut=True)
                Path(mf).write_text(json.dumps(man, indent=2), encoding="utf-8")
                print(f"✅ Wrote 'order' into manifest: {picked}")
                input("<enter>")

            elif sub == "11":
                mf, msg = _scrub_manifest_pos_order()
                print(f"{'✅' if mf else '⚠️'} {msg}")
                input("<enter>")

            else:
                print("Unknown selection."); input("<enter>")

        except Exception as e:
            print("Wizard error:", e); input("<enter>")

# ------------ Entry ------------
def main():
    run_menu()

if __name__ == "__main__":
    main()
