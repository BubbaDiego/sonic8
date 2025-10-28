
Native Perps Builder (placeholder)

What it does now

Builds a legacy Solana transaction with a Memo instruction that encodes your TP/SL intent.

Prints JSON: { unsignedTxBase64, requestPda: null, blockhash, lastValidBlockHeight }.

If NATIVE_SIGNER=1 and signer.txt is found, also prints { signedTxBase64, signature }.

Why legacy?
Legacy tx lets Python sign with solana easily. When you ship the real Perps builder, keep the same CLI I/O contract.

Input (stdin JSON)

{
  "op": "attach_tpsl",
  "params": {
    "owner": "<base58 pubkey>",
    "marketSymbol": "SOL-PERP",
    "isLong": true,
    "triggerPriceUsdAtomic": "197000000",
    "entirePosition": true,
    "sizeUsdDelta": null,
    "kind": "tp"
  }
}


Output (stdout JSON)

{
  "unsignedTxBase64": "...",
  "requestPda": null,
  "blockhash": "…",
  "lastValidBlockHeight": 123456
}


Plus optional signedTxBase64 and signature when NATIVE_SIGNER=1.

Env

SOLANA_RPC_URL (default mainnet)

SIGNER_PATH (optional; falls back to repo root signer.txt)

NATIVE_SIGNER=1 to sign in Node

SOLANA_DERIVATION_PATH (default m/44'/501'/0'/0')
