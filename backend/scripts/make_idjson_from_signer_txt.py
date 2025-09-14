#!/usr/bin/env python3
# Make a Solana CLI-style id.json from signer.txt (mnemonic or base58)
from __future__ import annotations

import json, os, sys

from typing import Optional, Dict
from solders.keypair import Keypair
from solders.pubkey import Pubkey

# --- CONFIG ---
SIGNER_TXT = r"C:\sonic5\signer.txt"
OUT_JSON   = r"C:\sonic5\backend\signer_id.json"
EXPECT_PUB = "CofTLEqPUXscsigdvP8YWkRTDmCQ6W7GKBVKRsZ6UvLn"  # sanity check

# ---- tiny base58 (no external dep) ----
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_IDX = {ch:i for i,ch in enumerate(_B58)}
def b58decode(s: str) -> bytes:
    n = 0
    for ch in s.strip():
        if ch not in _B58_IDX:
            raise ValueError(f"invalid base58 char: {ch}")
        n = n*58 + _B58_IDX[ch]
    full = n.to_bytes((n.bit_length()+7)//8, "big") if n else b"\x00"
    leading = 0
    for ch in s:
        if ch == "1": leading += 1
        else: break
    return b"\x00"*leading + full.lstrip(b"\x00")

def derive_from_mnemonic(mnemonic: str, passphrase: str = "") -> Keypair:
    try:
        from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
    except ImportError:
        raise RuntimeError("Install: pip install bip_utils pynacl")

    seed = Bip39SeedGenerator(mnemonic).Generate(passphrase)
    node = (Bip44.FromSeed(seed, Bip44Coins.SOLANA)
            .Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0))
    pk = node.PrivateKey()
    priv = None
    for attr in ("RawUncompressed","RawCompressed","Raw"):
        if hasattr(pk, attr):
            priv = getattr(pk, attr)().ToBytes(); break
    if not priv or len(priv) < 32:
        raise RuntimeError("could not extract 32-byte seed from bip_utils key")
    seed32 = priv[:32]
    # Try native seed, else PyNaCl fallback
    try:
        return Keypair.from_seed(seed32)
    except Exception:
        import nacl.signing as ns
        sk = ns.SigningKey(seed32)
        sec64 = sk.encode() + sk.verify_key.encode()
        return Keypair.from_bytes(sec64)

def keypair_from_base58(sec_b58: str) -> Keypair:
    raw = b58decode(sec_b58)
    if len(raw) == 64:
        return Keypair.from_bytes(raw)
    if len(raw) == 32:
        try:
            return Keypair.from_seed(raw)
        except Exception:
            import nacl.signing as ns
            sk = ns.SigningKey(raw)
            sec64 = sk.encode() + sk.verify_key.encode()
            return Keypair.from_bytes(sec64)
    raise ValueError(f"base58 secret length {len(raw)} not 32/64 bytes")

def parse_signer_txt(path: str) -> Dict[str,str]:
    txt = open(path, "r", encoding="utf-8").read()
    kv: Dict[str,str] = {}
    # Accept either key=value or key:value, ignore # comments
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        if "=" in line and ":" not in line:
            k,v = line.split("=",1)
        elif ":" in line and "=" not in line:
            k,v = line.split(":",1)
        else:
            # single token line → treat as base58
            kv["base58"] = line; continue
        kv[k.strip().lower()] = v.strip().strip('"').strip("'")
    return kv

def main():
    if not os.path.exists(SIGNER_TXT):
        print(f"signer.txt not found: {SIGNER_TXT}"); sys.exit(1)
    kv = parse_signer_txt(SIGNER_TXT)

    # priority: mnemonic/phrase → passphrase; else base58/secret/private
    kp: Optional[Keypair] = None
    mn = kv.get("mnemonic") or kv.get("phrase")
    if mn:
        pp = kv.get("passphrase","")
        kp = derive_from_mnemonic(mn, pp)
    else:
        sec = kv.get("base58") or kv.get("secret") or kv.get("private")
        if not sec:
            print("No mnemonic or base58 secret in signer.txt. Put either:\n"
                  "  mnemonic=<words>\n  [passphrase=<optional>]\n"
                  "OR\n  base58=<private_key_base58>\n  (also accepts secret= or private=)\n")
            sys.exit(1)
        kp = keypair_from_base58(sec)

    pub = str(kp.pubkey())
    print("Derived pubkey:", pub)
    if EXPECT_PUB and pub != EXPECT_PUB:
        print("WARN: derived pubkey != expected owner")
        print("  expected:", EXPECT_PUB)
        print("  derived :", pub)

    # write id.json as array of 64 ints
    sec64 = bytes(kp)  # solders Keypair serializes to 64-byte secret
    arr = list(sec64)
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(arr, f)
    print("Wrote id.json to:", OUT_JSON)

if __name__ == "__main__":
    main()
