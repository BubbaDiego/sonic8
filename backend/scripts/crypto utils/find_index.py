import sys
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
import nacl.signing, base58

MNEMONIC = "ginger snake rotate basic human column end bright anxiety craft bind finish"
TARGET   = "6yYacpjB2SiB1RVQ29YCEYioENYkwXfFhhetALp8uU8E"
MAX_IDX  = 25

seed = Bip39SeedGenerator(MNEMONIC).Generate()
for i in range(MAX_IDX + 1):
    ctx = (Bip44.FromSeed(seed, Bip44Coins.SOLANA)
           .Purpose().Coin().Account(i).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0))
    sk  = nacl.signing.SigningKey(ctx.PrivateKey().Raw().ToBytes())
    addr= base58.b58encode(sk.verify_key.encode()).decode()
    if addr == TARGET:
        print(f"{TARGET} ==> index {i}")
        sys.exit(0)
print("no match 0..", MAX_IDX)
