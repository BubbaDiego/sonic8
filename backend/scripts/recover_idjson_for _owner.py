#!/usr/bin/env python3
# Recover Solana id.json for a specific owner pubkey by scanning common derivation paths.
from __future__ import annotations
import json, os, sys
from typing import Optional, Dict, Tuple

TARGET_PUBKEY = "V8iveiirFvX7m7psPHWBJW85xPk1ZB6U4Ep9GUV2THW"
SIGNER_TXT    = r"C:\sonic5\signer.txt"          # contains mnemonic=/phrase= (+ passphrase=) OR base58=
OUT_JSON      = r"C:\sonic5\backend\signer_id.json"

# ---- tiny base58 ----
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_IDX = {ch:i for i,ch in enumerate(_B58)}
def b58decode(s: str) -> bytes:
    n = 0
    for ch in s.strip():
        if ch not in _B58_IDX: raise ValueError(f"invalid b58 char: {ch}")
        n = n*58 + _B58_IDX[ch]
    full = n.to_bytes((n.bit_length()+7)//8, "big") if n else b"\x00"
    leading = 0
    for ch in s:
        if ch=="1": leading+=1
        else: break
    return b"\x00"*leading + full.lstrip(b"\x00")

def parse_kv(path: str) -> Dict[str,str]:
    kv={}
    txt=open(path,"r",encoding="utf-8").read()
    for line in txt.splitlines():
        line=line.strip()
        if not line or line.startswith("#"): continue
        if "=" in line and ":" not in line: k,v=line.split("=",1)
        elif ":" in line and "=" not in line: k,v=line.split(":",1)
        else: kv["base58"]=line; continue
        kv[k.strip().lower()] = v.strip().strip('"').strip("'")
    return kv

def kp_from_base58(sec_b58: str):
    from solders.keypair import Keypair
    raw = b58decode(sec_b58)
    if len(raw)==64: return Keypair.from_bytes(raw)
    if len(raw)==32:
        try:
            return Keypair.from_seed(raw)
        except Exception:
            import nacl.signing as ns
            sk = ns.SigningKey(raw)
            sec64 = sk.encode()+sk.verify_key.encode()
            return Keypair.from_bytes(sec64)
    raise ValueError(f"base58 secret length {len(raw)} not 32/64")

def derive_from_mnemonic(mn: str, pp: str, acct: int, change: int, index: int):
    from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
    from solders.keypair import Keypair
    seed = Bip39SeedGenerator(mn).Generate(pp)
    node = Bip44.FromSeed(seed, Bip44Coins.SOLANA).Purpose().Coin().Account(acct).Change(Bip44Changes.CHAIN_EXT if change==0 else Bip44Changes.CHAIN_INT).AddressIndex(index)
    pk = node.PrivateKey()
    priv = None
    for attr in ("RawUncompressed","RawCompressed","Raw"):
        if hasattr(pk, attr):
            priv = getattr(pk, attr)().ToBytes(); break
    if not priv or len(priv) < 32:
        raise RuntimeError("could not extract 32-byte seed")
    seed32 = priv[:32]
    try:
        return Keypair.from_seed(seed32)
    except Exception:
        import nacl.signing as ns
        sk = ns.SigningKey(seed32)
        sec64 = sk.encode()+sk.verify_key.encode()
        return Keypair.from_bytes(sec64)

def main():
    if not os.path.exists(SIGNER_TXT):
        print("signer.txt not found:", SIGNER_TXT); sys.exit(1)
    kv = parse_kv(SIGNER_TXT)
    target = TARGET_PUBKEY.strip()

    # If a base58 secret is present, try that first
    sec = kv.get("base58") or kv.get("secret") or kv.get("private")
    if sec:
        kp = kp_from_base58(sec)
        print("Derived pubkey from base58:", kp.pubkey())
        if str(kp.pubkey()) == target:
            arr = list(bytes(kp))
            os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
            json.dump(arr, open(OUT_JSON,"w",encoding="utf-8"))
            print("Wrote id.json:", OUT_JSON)
            return
        else:
            print("Base58 secret does not match target owner.")

    # Else try mnemonic + optional passphrase across common paths
    mn = kv.get("mnemonic") or kv.get("phrase")
    if not mn:
        print("No mnemonic/phrase or base58 secret in signer.txt.")
        print("Add either:\n  mnemonic=<12–24 words>\n  [passphrase=<optional>]\nOR\n  base58=<private_key_base58>\n")
        sys.exit(1)

    pp = kv.get("passphrase","")

    tried=0
    print("Brute-forcing common Solana paths to locate the owner pubkey…")
    for acct in range(0, 10):           # account'
        for change in (0,1):            # change'
            for idx in range(0, 10):    # address index
                tried += 1
                try:
                    kp = derive_from_mnemonic(mn, pp, acct, change, idx)
                except Exception as e:
                    print("derive error:", e); sys.exit(1)
                if str(kp.pubkey()) == target:
                    print(f"FOUND at path m/44'/501'/{acct}'/{change}' index {idx}")
                    arr = list(bytes(kp))
                    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
                    json.dump(arr, open(OUT_JSON,"w",encoding="utf-8"))
                    print("Wrote id.json:", OUT_JSON)
                    return
                if tried % 25 == 0:
                    print(f"…checked {tried} candidates; latest pubkey {kp.pubkey()}")
    print("No match found. Either the mnemonic/passphrase is for a different wallet, or the wallet was exported as a base58 secret (try putting base58=… in signer.txt).")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
