# backend/services/signer_loader.py
from __future__ import annotations

import base64
import json
import os
import re
import struct
import subprocess
import unicodedata
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from solders.keypair import Keypair
import hashlib
import hmac

# ---------------------------------------------------------------------
# Configuration & global state
# ---------------------------------------------------------------------
DEFAULT_SIGNER_PATH = os.getenv("SONIC_SIGNER_PATH", "signer.txt")
MNEMONIC_CMD = os.getenv("SONIC_MNEMONIC_DERIVE_CMD", "")  # e.g. "python backend/scripts/derive_keypair.py --stdin-json"
ENV_PROJECT_ROOTS = [
    os.getenv("SONIC_PROJECT_ROOT", ""),
    os.getenv("PROJECT_ROOT", ""),
    os.getenv("PWD", ""),
]

MNEMONIC_RE = re.compile(r"^([a-z]+(?:\s+[a-z]+){11,23})$", re.IGNORECASE)

# Accept common aliases
MNEMONIC_KEYS = {
    "mnemonic", "phrase", "seed_phrase", "seedPhrase",
    "secret_recovery_phrase", "secretRecoveryPhrase",
    "recovery_phrase", "recoveryPhrase"
}
PASSPHRASE_KEYS = {"passphrase", "mnemonic_passphrase", "bip39_passphrase", "password"}
SECRET_ARRAY_KEYS = {"secretKey", "secret_key"}       # array[int] like id.json
PRIVATE_STRING_KEYS = {"privateKey", "private_key"}   # base64/base58 string (optional)
ADDRESS_KEYS = {"public_address", "address", "pubkey"}  # informational; not used to derive

# Last successful load meta (exposed via /signer/info)
SIGNER_INFO: Dict[str, str] = {"method": "unknown", "path": "", "note": ""}


# ---------------------------------------------------------------------
# Small crypto helpers for native BIP39 + SLIP-0010 (ed25519)
# ---------------------------------------------------------------------
def _nfkd(s: str) -> str:
    return unicodedata.normalize("NFKD", s)

def _bip39_seed(mnemonic: str, passphrase: str = "") -> bytes:
    # PBKDF2-HMAC-SHA512(mnemonic, "mnemonic"+passphrase, 2048, 64)
    password = _nfkd(mnemonic)
    salt = "mnemonic" + _nfkd(passphrase or "")
    return hashlib.pbkdf2_hmac("sha512", password.encode(), salt.encode(), 2048, dklen=64)

def _slip10_ed25519_master(seed: bytes) -> Tuple[bytes, bytes]:
    I = hmac.new(b"ed25519 seed", seed, hashlib.sha512).digest()
    return I[:32], I[32:]  # (k, c)

def _slip10_ed25519_ckd_priv(k_par: bytes, c_par: bytes, index: int) -> Tuple[bytes, bytes]:
    # hardened only (ed25519)
    if index < 0x80000000:
        index |= 0x80000000
    data = b"\x00" + k_par + struct.pack(">I", index)
    I = hmac.new(c_par, data, hashlib.sha512).digest()
    return I[:32], I[32:]  # (k_i, c_i)

def _derive_solana_key(mnemonic: str, passphrase: str = "", path: str = "m/44'/501'/0'/0'") -> bytes:
    seed = _bip39_seed(mnemonic, passphrase)
    k, c = _slip10_ed25519_master(seed)

    # parse path like m/44'/501'/0'/0'
    if not path.startswith("m/"):
        raise ValueError("derivation path must start with m/")
    segments = path[2:].split("/")
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        hardened = seg.endswith("'")
        num = int(seg[:-1] if hardened else seg)
        idx = num | 0x80000000  # ed25519 requires hardened
        k, c = _slip10_ed25519_ckd_priv(k, c, idx)
    return k  # 32-byte seed suitable for ed25519


# ---------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------
def _candidate_paths(spec: str) -> List[Path]:
    cand: List[Path] = []
    raw = Path(spec)
    if raw.is_absolute():
        cand.append(raw)
    else:
        cwd = Path.cwd()
        here = Path(__file__).resolve().parent       # backend/services
        backend_dir = here.parent                    # backend
        repo_root = backend_dir.parent               # project root

        cand.extend([cwd / spec, here / spec, backend_dir / spec, repo_root / spec])
        for root in ENV_PROJECT_ROOTS:
            if root:
                cand.append(Path(root) / spec)

    # dedupe
    seen = set()
    uniq: List[Path] = []
    for p in cand:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        k = str(rp)
        if k not in seen:
            seen.add(k)
            uniq.append(Path(k))
    return uniq

def _resolve_existing(spec: str) -> Tuple[Optional[Path], List[str]]:
    tried: List[str] = []
    for p in _candidate_paths(spec):
        tried.append(str(p))
        if p.exists():
            return p, tried
    return None, tried

def _mark(kp: Keypair, method: str, path: str, note: str = "") -> Keypair:
    SIGNER_INFO.update({"method": method, "path": path, "note": note, "pubkey": str(kp.pubkey())})
    return kp


# ---------------------------------------------------------------------
# Parsers (formats)
# ---------------------------------------------------------------------
def _try_json_array(raw: str, path: str):
    try:
        arr = json.loads(raw)
        if isinstance(arr, list) and len(arr) in (32, 64) and all(isinstance(x, int) for x in arr):
            b = bytes(arr)
            kp = Keypair.from_bytes(b) if len(b) == 64 else Keypair.from_seed(b)
            return _mark(kp, "json_array", path), None
        return None, "not a json array id.json"
    except Exception as e:
        return None, f"json parse failed: {type(e).__name__}: {e}"

def _try_base64(raw: str, path: str):
    try:
        b = base64.b64decode(raw)
        if len(b) in (32, 64):
            kp = Keypair.from_bytes(b) if len(b) == 64 else Keypair.from_seed(b)
            return _mark(kp, "base64", path), None
        return None, f"base64 length {len(b)} not 32/64"
    except Exception as e:
        return None, f"base64 decode failed: {type(e).__name__}: {e}"

def _normalize_kv_text(raw: str) -> Dict[str, str]:
    # allow separators: newline / ; / , / & / spaces
    txt = raw.replace("&", "\n").replace(";", "\n").replace(",", "\n")
    pairs: Dict[str, str] = {}
    for line in txt.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip().strip('"').strip("'")
        v = v.strip().strip('"').strip("'")
        if k:
            pairs[k] = v
    # also match "k=v" tokens separated by spaces
    for k, v in re.findall(r"(\w+)\s*=\s*([^\s]+)", raw):
        pairs.setdefault(k, v)
    return pairs

def _derive_from_mnemonic_native(mnemonic: str, path: str, passphrase: str = ""):
    try:
        seed32 = _derive_solana_key(mnemonic, passphrase, "m/44'/501'/0'/0'")
        kp = Keypair.from_seed(seed32)
        note = "native SLIP-0010 @ m/44'/501'/0'/0'"
        if passphrase:
            note += " (with bip39 passphrase)"
        return _mark(kp, "mnemonic:native", path, note), None
    except Exception as e:
        return None, f"native derive failed: {type(e).__name__}: {e}"

def _derive_from_mnemonic_bip_utils(mnemonic: str, path: str, passphrase: str = ""):
    try:
        from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
    except Exception as e:
        return None, f"bip_utils not installed: {e}"

    try:
        if not Bip39MnemonicValidator(mnemonic).Validate():
            return None, "invalid mnemonic (bip_utils validator)"
        seed = Bip39SeedGenerator(mnemonic).Generate(passphrase or "")
        ctx = Bip44.FromSeed(seed, Bip44Coins.SOLANA).Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
        priv32 = ctx.PrivateKey().Raw().ToBytes()[:32]
        kp = Keypair.from_seed(priv32)
        note = "bip_utils @ m/44'/501'/0'/0'"
        if passphrase:
            note += " (with bip39 passphrase)"
        return _mark(kp, "mnemonic:bip_utils", path, note), None
    except Exception as e:
        return None, f"bip_utils derive failed: {type(e).__name__}: {e}"

def _derive_from_mnemonic_external(mnemonic: str, path: str, passphrase: str = ""):
    if not MNEMONIC_CMD:
        return None, "no external derive command configured (set SONIC_MNEMONIC_DERIVE_CMD)"
    try:
        cmd = MNEMONIC_CMD
        if "{mnemonic}" in cmd or "{passphrase}" in cmd:
            cmd = cmd.format(mnemonic=mnemonic, passphrase=passphrase)
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        else:
            stdin_payload = mnemonic if not passphrase else f"{mnemonic}\n{passphrase}"
            proc = subprocess.run(MNEMONIC_CMD, input=stdin_payload, shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            return None, f"derive cmd exit {proc.returncode}: {proc.stderr.strip()}"
        arr = json.loads(proc.stdout)
        if not (isinstance(arr, list) and len(arr) in (32, 64) and all(isinstance(x, int) for x in arr)):
            return None, f"unexpected derive output: {proc.stdout[:160]}"
        b = bytes(arr)
        kp = Keypair.from_bytes(b) if len(b) == 64 else Keypair.from_seed(b)
        note = f"external: {MNEMONIC_CMD}"
        if passphrase:
            note += " (with bip39 passphrase)"
        return _mark(kp, "mnemonic:external", path, note), None
    except Exception as e:
        return None, f"external derive failed: {type(e).__name__}: {e}"

def _try_json_object(raw: str, path: str):
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return None, "json is not an object"
        # secretKey array
        for key in SECRET_ARRAY_KEYS:
            if key in obj and isinstance(obj[key], list) and all(isinstance(x, int) for x in obj[key]):
                arr = obj[key]
                if len(arr) in (32, 64):
                    b = bytes(arr)
                    kp = Keypair.from_bytes(b) if len(b) == 64 else Keypair.from_seed(b)
                    return _mark(kp, f"json_object:{key}", path), None
        # mnemonic + optional passphrase
        mnemonic = None
        passphrase = ""
        for mk in MNEMONIC_KEYS:
            if mk in obj and isinstance(obj[mk], str):
                mnemonic = obj[mk].strip()
                break
        for pk in PASSPHRASE_KEYS:
            if pk in obj and isinstance(obj[pk], str):
                passphrase = obj[pk].strip()
                break
        if mnemonic:
            for derive in (_derive_from_mnemonic_native, _derive_from_mnemonic_bip_utils, _derive_from_mnemonic_external):
                kp, err = derive(mnemonic, path, passphrase)
                if kp is not None:
                    return kp, None
            return None, "mnemonic derive failed (all methods)"
        # privateKey string
        for sk in PRIVATE_STRING_KEYS:
            if sk in obj and isinstance(obj[sk], str):
                s = obj[sk].strip()
                # base64
                try:
                    b = base64.b64decode(s)
                    if len(b) in (32, 64):
                        kp = Keypair.from_bytes(b) if len(b) == 64 else Keypair.from_seed(b)
                        return _mark(kp, f"json_object:{sk}:base64", path), None
                except Exception:
                    pass
                # base58
                try:
                    import base58  # type: ignore
                    b = base58.b58decode(s)
                    if len(b) in (32, 64):
                        kp = Keypair.from_bytes(b) if len(b) == 64 else Keypair.from_seed(b)
                        return _mark(kp, f"json_object:{sk}:base58", path), None
                except Exception as e:
                    return None, f"{sk} decode failed: {e}"
        return None, "json object did not contain known keys"
    except Exception as e:
        return None, f"json object parse failed: {type(e).__name__}: {e}"

def _try_kv_pairs(raw: str, path: str):
    pairs = _normalize_kv_text(raw)
    if not pairs:
        return None, "no key=value pairs detected"

    # mnemonic + optional passphrase
    mnemonic = None
    passphrase = ""
    for mk in MNEMONIC_KEYS:
        if mk in pairs and isinstance(pairs[mk], str):
            mnemonic = pairs[mk].strip()
            break
    for pk in PASSPHRASE_KEYS:
        if pk in pairs and isinstance(pairs[pk], str):
            passphrase = pairs[pk].strip()
            break

    if mnemonic:
        for derive in (_derive_from_mnemonic_native, _derive_from_mnemonic_bip_utils, _derive_from_mnemonic_external):
            kp, err = derive(mnemonic, path, passphrase)
            if kp is not None:
                return kp, None
        return None, "mnemonic derive failed (all methods)"

    # secretKey as JSON array embedded?
    for key in SECRET_ARRAY_KEYS:
        if key in pairs:
            try:
                arr = json.loads(pairs[key])
                if isinstance(arr, list) and len(arr) in (32, 64) and all(isinstance(x, int) for x in arr):
                    b = bytes(arr)
                    kp = Keypair.from_bytes(b) if len(b) == 64 else Keypair.from_seed(b)
                    return _mark(kp, f"kv_pairs:{key}", path), None
            except Exception:
                pass

    return None, "kv pairs did not include mnemonic/phrase or secret key"

def _try_mnemonic_raw(raw: str, path: str):
    text = raw.strip()
    if not MNEMONIC_RE.match(text):
        return None, "not a 12–24 word mnemonic"
    for derive in (_derive_from_mnemonic_native, _derive_from_mnemonic_bip_utils, _derive_from_mnemonic_external):
        kp, err = derive(text, path, "")
        if kp is not None:
            return kp, None
    return None, "mnemonic derive failed (all methods)"


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def load_signer(path: Optional[str] = None) -> Keypair:
    spec = path or DEFAULT_SIGNER_PATH
    resolved, tried = _resolve_existing(spec)
    if resolved is None:
        raise FileNotFoundError(f"Signer file not found: {spec}. Tried: {tried}")

    raw = resolved.read_text(encoding="utf-8").strip()
    rpath = str(resolved)

    for fn in (
        _try_json_array,    # id.json
        _try_base64,        # base64 blob
        _try_json_object,   # {"mnemonic": "..."} / {"secretKey":[...]} / {"privateKey":"..."}
        _try_kv_pairs,      # address=..., mnemonic=..., passphrase=...
        _try_mnemonic_raw,  # plain mnemonic
    ):
        kp, err = fn(raw, rpath)
        if kp is not None:
            return kp
    raise ValueError(
        "Unsupported signer format. Use one of:\n"
        "- Solana id.json (array of 64 ints), or\n"
        "- base64 secret (32/64 bytes), or\n"
        "- JSON object with { mnemonic | phrase [, passphrase] } or { secretKey:[...] }, or\n"
        "- key=value text including mnemonic=... (alias: phrase=...), or\n"
        "- plain BIP39 mnemonic (12–24 words)."
    )

def signer_info() -> Dict[str, str]:
    return SIGNER_INFO.copy()

def diagnose_signer() -> Dict[str, Any]:
    spec = DEFAULT_SIGNER_PATH
    cand = _candidate_paths(spec)
    existing = [str(p) for p in cand if p.exists()]
    first = existing[0] if existing else None

    out: Dict[str, Any] = {
        "spec": spec,
        "cwd": str(Path.cwd()),
        "module_dir": str(Path(__file__).resolve().parent),
        "candidates": [str(p) for p in cand],
        "found": first or "",
        "exists": bool(first),
    }
    if not first:
        out["error"] = "no candidate signer.txt found"
        return out

    raw = Path(first).read_text(encoding="utf-8").strip()
    if MNEMONIC_RE.match(raw):
        words = raw.split()
        out["content_type_guess"] = "mnemonic"
        out["preview"] = f"{' '.join(words[:2])} … {' '.join(words[-2:])}"
    else:
        out["content_type_guess"] = "json_or_base64_or_kv"
        out["preview"] = f"{raw[:10]}…{raw[-6:]} (len={len(raw)})"

    checks = {}
    for name, fn in (
        ("json_array", _try_json_array),
        ("base64", _try_base64),
        ("json_object", _try_json_object),
        ("kv_pairs", _try_kv_pairs),
        ("mnemonic_raw", _try_mnemonic_raw),
    ):
        try:
            kp, err = fn(raw, first)
            if kp is not None:
                checks[name] = {"ok": True, "pubkey": str(kp.pubkey())}
            else:
                checks[name] = {"ok": False, "error": err}
        except Exception as e:
            checks[name] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    out["checks"] = checks
    out["final"] = signer_info()
    return out
