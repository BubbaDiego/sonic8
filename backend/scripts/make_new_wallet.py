#!/usr/bin/env python3
# Create a brand-new Solana wallet; write signer.txt and signer_id.json
from __future__ import annotations

import os, json, sys
from typing import Optional

# ====== CONFIG (edit if you like) ======
OUT_DIR       = r"C:\sonic5\backend"        # where files will be written
WORDS         = 12                           # 12 or 24
PASSPHRASE    = ""                           # optional BIP39 passphrase; "" means none
SIGNER_TXT    = os.path.join(OUT_DIR, "signer.txt")
ID_JSON       = os.path.join(OUT_DIR, "signer_id.json")
# ======================================

# tiny base58 (no external dep)
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58enc(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = _B58[0] if n == 0 else ""
    out=[]
    while n:
        n,r = divmod(n,58)
        out.append(_B58[r])
    if out: s += "".join(reversed(out))
    z=0
    for ch in b:
        if ch==0: z+=1
        else: break
    return (_B58[0]*z)+s

def main():
    try:
        from bip_utils import Bip39MnemonicGenerator, Bip39WordsNum, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
        import nacl.signing as ns
        from solders.keypair import Keypair
    except ImportError:
        print("Install deps first:\n  pip install bip_utils pynacl solders", file=sys.stderr)
        sys.exit(1)

    # 1) create mnemonic
    words_num = Bip39WordsNum.WORDS_NUM_12 if WORDS == 12 else Bip39WordsNum.WORDS_NUM_24
    mnemonic  = Bip39MnemonicGenerator().FromWordsNumber(words_num)

    # 2) derive Solana key: m/44'/501'/0'/0'
    seed = Bip39SeedGenerator(mnemonic).Generate(PASSPHRASE)
    node = (Bip44.FromSeed(seed, Bip44Coins.SOLANA)
            .Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0))

    # private key bytes (handle different bip_utils versions)
    pk_obj = node.PrivateKey()
    priv = None
    for attr in ("RawUncompressed","RawCompressed","Raw"):
        if hasattr(pk_obj, attr):
            priv = getattr(pk_obj, attr)().ToBytes()
            break
    if not priv or len(priv) < 32:
        print("Could not extract private key bytes from bip_utils; update bip_utils", file=sys.stderr)
        sys.exit(1)
    seed32 = priv[:32]

    # build keypair (solders)
    try:
        kp = Keypair.from_seed(seed32)
    except Exception:
        # fallback via pynacl
        sk = ns.SigningKey(seed32)
        sec64 = sk.encode() + sk.verify_key.encode()
        kp = Keypair.from_bytes(sec64)

    pub  = str(kp.pubkey())
    sec64 = bytes(kp)                  # 64-byte secret key for id.json
    sec_b58 = b58enc(sec64)            # base58 string (handy for wallets/exports)

    os.makedirs(OUT_DIR, exist_ok=True)

    # 3) write signer.txt (key=value)
    with open(SIGNER_TXT, "w", encoding="utf-8") as f:
        f.write("# DO NOT SHARE THIS FILE. This is a brand-new wallet.\n")
        f.write(f"address={pub}\n")
        f.write(f"mnemonic=\"{mnemonic}\"\n")
        f.write(f"passphrase=\"{PASSPHRASE}\"\n")
        f.write(f"base58={sec_b58}\n")
    # 4) write id.json
    with open(ID_JSON, "w", encoding="utf-8") as f:
        json.dump(list(sec64), f)

    print("✅ New wallet created")
    print("  Address:   ", pub)
    print("  signer.txt:", SIGNER_TXT)
    print("  id.json:   ", ID_JSON)
    print("\nIMPORTANT: write down your mnemonic safely. Anyone with it controls this wallet.")
    print(f"\nMnemonic:\n{mnemonic}\n")

if __name__ == "__main__":
    main()
