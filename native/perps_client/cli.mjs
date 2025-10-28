#!/usr/bin/env node
/**

Native Perps Builder (placeholder)

Reads JSON from stdin, builds a legacy Transaction with a Memo instruction

carrying your TP/SL request details. Returns:

{ unsignedTxBase64, requestPda: null, blockhash, lastValidBlockHeight }

Optional: set NATIVE_SIGNER=1 to sign with signer.txt (see SIGNER_PATH env or repo root).

Then output also: { signedTxBase64, signature }

Replace the buildMemoTx with real Perps PositionRequest construction later.
*/
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { Connection, PublicKey, Transaction, TransactionInstruction, Keypair } from "@solana/web3.js";
import bs58 from "bs58";
import * as bip39 from "bip39";
import { derivePath as ed25519DerivePath } from "ed25519-hd-key";
import nacl from "tweetnacl";

const MEMO_PROGRAM_ID = new PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr");

function readAllStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => (data += c));
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

function findSignerTxt() {
  const envPath = process.env.SIGNER_PATH;
  if (envPath && fs.existsSync(envPath)) return envPath;
  const here = process.cwd();
  const candidate = path.join(here, "signer.txt");
  if (fs.existsSync(candidate)) return candidate;
  // climb a few parents looking for repo root + signer.txt
  let p = path.dirname(fileURLToPath(import.meta.url));
  for (let i = 0; i < 8; i++) {
    const test = path.join(p, "signer.txt");
    if (fs.existsSync(test)) return test;
    const parent = path.dirname(p);
    if (parent === p) break;
    p = parent;
  }
  return null;
}

function parseSignerFile(pathname) {
  const txt = fs.readFileSync(pathname, "utf8").trim();
  const pass = /(?:passphrase|mnemonic)\s*[:=]\s*(.+)/i.exec(txt)?.[1] ?? txt.split("\n").find((l) => l.trim()) ?? "";
  const phrase = pass.trim().replace(/^['"]|['"]$/g, "");
  const seedPass = /(?:bip39_passphrase|seed_passphrase)\s*[:=]\s*(.+)/i.exec(txt)?.[1]?.trim()?.replace(/^['"]|['"]$/g, "") ?? "";
  const words = phrase.split(/\s+/);
  if (words.length < 12) throw new Error("signer.txt does not contain a valid mnemonic");
  return { mnemonic: words.join(" "), bip39Passphrase: seedPass };
}

function keypairFromMnemonic(mnemonic, bip39Passphrase, derivationPath = "m/44'/501'/0'/0'") {
  const seed = bip39.mnemonicToSeedSync(mnemonic, bip39Passphrase || "");
  const { key } = ed25519DerivePath(derivationPath, seed.toString("hex"));
  const kp = nacl.sign.keyPair.fromSeed(key); // 32-byte seed → 64-byte secretKey
  return Keypair.fromSecretKey(Buffer.from(kp.secretKey));
}

async function buildMemoTx({ owner, memoJson, rpc }) {
  const connection = new Connection(rpc, "finalized");
  const payer = new PublicKey(owner);
  const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash("finalized");

  const ix = new TransactionInstruction({
    keys: [],
    programId: MEMO_PROGRAM_ID,
    data: Buffer.from(memoJson, "utf8"),
  });

  const tx = new Transaction({ feePayer: payer, recentBlockhash: blockhash });
  tx.add(ix);
  const unsignedTxBase64 = Buffer.from(
    tx.serialize({ requireAllSignatures: false, verifySignatures: false })
  ).toString("base64");
  return { unsignedTxBase64, blockhash, lastValidBlockHeight, tx };
}

async function main() {
  const raw = await readAllStdin();
  const body = JSON.parse(raw || "{}");
  if (body.op !== "attach_tpsl") throw new Error(`Unsupported op: ${body.op || "<none>"}`);

  const p = body.params || {};
  const owner = p.owner;
  if (!owner) throw new Error("params.owner required");

  const rpc = process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com";
  const memoJson = JSON.stringify({
    tag: "JUP-PERPS-TPSL",
    kind: p.kind, // "tp" | "sl"
    marketSymbol: p.marketSymbol || "UNKNOWN",
    isLong: !!p.isLong,
    triggerPriceUsdAtomic: String(p.triggerPriceUsdAtomic || ""),
    entirePosition: !!p.entirePosition,
    sizeUsdDelta: p.sizeUsdDelta ? String(p.sizeUsdDelta) : null,
  });

  const { unsignedTxBase64, blockhash, lastValidBlockHeight, tx } = await buildMemoTx({
    owner,
    memoJson,
    rpc,
  });

  const out = { unsignedTxBase64, requestPda: null, blockhash, lastValidBlockHeight };

  // Optional native signing (keeps secrets in Node). Not sent; Python will submit.
  if (process.env.NATIVE_SIGNER === "1") {
    const signerPath = findSignerTxt();
    if (!signerPath)
      throw new Error("NATIVE_SIGNER=1 but signer.txt not found (set SIGNER_PATH or place at repo root)");
    const { mnemonic, bip39Passphrase } = parseSignerFile(signerPath);
    const kp = keypairFromMnemonic(
      mnemonic,
      bip39Passphrase,
      process.env.SOLANA_DERIVATION_PATH || "m/44'/501'/0'/0'"
    );
    tx.sign(kp);
    const signedTxBase64 = Buffer.from(
      tx.serialize({ requireAllSignatures: false, verifySignatures: false })
    ).toString("base64");
    out.signedTxBase64 = signedTxBase64;
    try {
      out.signature = bs58.encode(tx.signatures[0].signature);
    } catch {
      /* ignore */
    }
  }

  process.stdout.write(JSON.stringify(out));
}

main().catch((err) => {
  console.error(err.stack || String(err));
  process.exit(1);
});
