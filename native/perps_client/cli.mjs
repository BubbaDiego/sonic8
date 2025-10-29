#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { Connection, PublicKey, Transaction, ComputeBudgetProgram, Keypair } from "@solana/web3.js";
import * as anchor from "@coral-xyz/anchor";
import bs58 from "bs58";
import * as bip39 from "bip39";
import { derivePath as ed25519DerivePath } from "ed25519-hd-key";
import nacl from "tweetnacl";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function readAllStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => (data += c));
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

function ensureConfigPath() {
  const cfg = path.join(__dirname, "config.json");
  const ex = path.join(__dirname, "config.example.json");
  if (!fs.existsSync(cfg) && fs.existsSync(ex)) {
    try {
      fs.copyFileSync(ex, cfg);
    } catch {}
  }
  return cfg;
}

function loadConfig() {
  const cfgPath = ensureConfigPath();
  if (!fs.existsSync(cfgPath)) {
    throw new Error(`Missing ${cfgPath}. Copy config.example.json to config.json and fill values.`);
  }
  const j = JSON.parse(fs.readFileSync(cfgPath, "utf8"));

  if (process.env.JUP_PERPS_PROGRAM_ID) j.programId = process.env.JUP_PERPS_PROGRAM_ID;
  if (process.env.JUP_PERPS_IDL) j.idlPath = process.env.JUP_PERPS_IDL;
  if (process.env.JUP_PERPS_METHOD_TRIGGER) j.methodTrigger = process.env.JUP_PERPS_METHOD_TRIGGER;
  if (process.env.JUP_PERPS_MICROLAMPORTS) {
    j.computeUnitPriceMicrolamports = Number(process.env.JUP_PERPS_MICROLAMPORTS);
  }

  if (!j.programId || !j.idlPath || !j.methodTrigger) {
    throw new Error("config.json must set programId, idlPath, methodTrigger");
  }

  const idlFull = path.isAbsolute(j.idlPath) ? path.normalize(j.idlPath) : path.join(__dirname, j.idlPath);
  if (!fs.existsSync(idlFull)) {
    throw new Error(`IDL not found at ${idlFull}`);
  }
  j._idlFull = idlFull;
  if (process.env.DEBUG_NATIVE === "1") {
    console.error("[DEBUG] programId", j.programId);
    console.error("[DEBUG] idlPath", j._idlFull);
    console.error("[DEBUG] methodTrigger", j.methodTrigger);
  }
  try {
    new PublicKey(j.programId);
  } catch (e) {
    throw new Error(`config.programId is invalid or empty: '${j.programId}'. Set programId or JUP_PERPS_PROGRAM_ID.`);
  }
  return j;
}

function findSignerTxt() {
  const envPath = process.env.SIGNER_PATH;
  if (envPath && fs.existsSync(envPath)) return envPath;
  const candidate = path.join(process.cwd(), "signer.txt");
  if (fs.existsSync(candidate)) return candidate;
  return null;
}

function parseSignerFile(p) {
  const txt = fs.readFileSync(p, "utf8").trim();
  const m = /(?:passphrase|mnemonic)\s*[:=]\s*(.+)/i.exec(txt);
  const phrase = (m ? m[1] : txt.split("\n").find((l) => l.trim()) || "").trim().replace(/^["']|["']$/g, "");
  const m2 = /(?:bip39_passphrase|seed_passphrase)\s*[:=]\s*(.+)/i.exec(txt);
  const pass = (m2 ? m2[1] : "").trim().replace(/^["']|["']$/g, "");
  const words = phrase.split(/\s+/);
  if (words.length < 12) throw new Error("signer.txt does not contain a valid mnemonic");
  return { mnemonic: words.join(" "), bip39Passphrase: pass };
}

function keypairFromMnemonic(mnemonic, bip39Passphrase, pathStr = "m/44'/501'/0'/0'") {
  const seed = bip39.mnemonicToSeedSync(mnemonic, bip39Passphrase || "");
  const { key } = ed25519DerivePath(pathStr, seed.toString("hex"));
  const kp = nacl.sign.keyPair.fromSeed(key);
  return Keypair.fromSecretKey(Buffer.from(kp.secretKey));
}

function mapMarketSymbol(sym) {
  const s = String(sym || "").toUpperCase();
  if (s.startsWith("SOL")) return "SOL";
  if (s.startsWith("ETH")) return "ETH";
  if (s.startsWith("BTC")) return "BTC";
  return s;
}

function resolveAccounts(context, cfg, marketKey) {
  const row = (context && context.positionRow) || {};
  const a = {};
  const tryRow = (k) => row[k] || row[`${k}_pda`] || row[`${k}Pda`] || row[`${k}Pubkey`];

  a.owner = row.owner || row.owner_pubkey || row.public_key || null;
  a.position = tryRow("position") || tryRow("position_account") || null;
  a.group = tryRow("group") || null;
  a.pool = tryRow("pool") || null;
  a.custody = tryRow("custody") || null;
  a.collateralCustody = tryRow("collateral_custody") || tryRow("collateralCustody") || null;
  a.oracle = tryRow("oracle") || null;

  const mk = (cfg.markets && cfg.markets[marketKey]) || {};
  a.group = a.group || mk.group || null;
  a.pool = a.pool || mk.pool || null;
  a.custody = a.custody || mk.custody || null;
  a.collateralCustody = a.collateralCustody || mk.collateralCustody || null;
  a.oracle = a.oracle || mk.oracle || null;

  const required = ["group", "pool", "custody", "collateralCustody"];
  const missing = required.filter((k) => !a[k]);
  if (missing.length) {
    throw new Error(`Missing required Perps accounts: ${missing.join(", ")}.`);
  }
  return a;
}

function composeTriggerArgs(params, isLong) {
  const kind = (params.kind || "tp").toLowerCase();
  let above;
  if (isLong) above = kind === "tp";
  else above = kind === "sl";
  const sizeUsdDelta = params.sizeUsdDelta ? BigInt(params.sizeUsdDelta) : null;
  const triggerPrice = BigInt(params.triggerPriceUsdAtomic);
  return { triggerPrice, triggerAboveThreshold: above, entirePosition: !!params.entirePosition, sizeUsdDelta };
}

async function buildPerpsTriggerTx({ cfg, idl, owner, params, context }) {
  const connection = new Connection(process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com", "confirmed");
  const programId = new PublicKey(cfg.programId);
  const payerPubkey = new PublicKey(owner);

  const dummyWallet = {
    publicKey: payerPubkey,
    signTransaction: async (tx) => tx,
    signAllTransactions: async (txs) => txs
  };
  const provider = new anchor.AnchorProvider(connection, dummyWallet, { commitment: "confirmed" });
  const program = new anchor.Program(idl, programId, provider);

  const marketKey = mapMarketSymbol(params.marketSymbol);
  const accs = resolveAccounts(context, cfg, marketKey);
  const trigger = composeTriggerArgs(params, !!params.isLong);

  const methodName = cfg.methodTrigger;
  const methodFn = program.methods[methodName];
  if (typeof methodFn !== "function") {
    throw new Error(`IDL method '${methodName}' not found — set config.methodTrigger to match your IDL.`);
  }

  const accounts = {
    owner: payerPubkey,
    group: new PublicKey(accs.group),
    pool: new PublicKey(accs.pool),
    custody: new PublicKey(accs.custody),
    collateralCustody: new PublicKey(accs.collateralCustody),
    ...(accs.position ? { position: new PublicKey(accs.position) } : {}),
  };

  const args = {
    requestType: { trigger: {} },
    triggerPrice: new anchor.BN(trigger.triggerPrice.toString()),
    triggerAboveThreshold: trigger.triggerAboveThreshold,
    entirePosition: trigger.entirePosition,
    sizeUsdDelta: trigger.sizeUsdDelta !== null ? new anchor.BN(trigger.sizeUsdDelta.toString()) : null,
  };

  const ixBuilder = methodFn(args);
  if (!ixBuilder || typeof ixBuilder.accounts !== "function") {
    throw new Error(`IDL method '${methodName}' does not accept the provided arguments.`);
  }
  const ix = await ixBuilder.accounts(accounts).instruction();

  const cuPrice = Number(cfg.computeUnitPriceMicrolamports || 0);
  const ixs = [];
  if (cuPrice > 0) ixs.push(ComputeBudgetProgram.setComputeUnitPrice({ microLamports: cuPrice }));
  ixs.push(ix);

  const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash("finalized");
  const tx = new Transaction({ feePayer: payerPubkey, recentBlockhash: blockhash }).add(...ixs);
  const unsignedTxBase64 = Buffer.from(tx.serialize({ requireAllSignatures: false, verifySignatures: false })).toString("base64");
  return { unsignedTxBase64, requestPda: null, blockhash, lastValidBlockHeight, tx };
}

function maybeNativeSign(tx) {
  if (process.env.NATIVE_SIGNER !== "1") return null;
  const signerPath = findSignerTxt();
  if (!signerPath) throw new Error("NATIVE_SIGNER=1 but signer.txt not found (set SIGNER_PATH or place at repo root)");
  const { mnemonic, bip39Passphrase } = parseSignerFile(signerPath);
  const kp = keypairFromMnemonic(mnemonic, bip39Passphrase, process.env.SOLANA_DERIVATION_PATH || "m/44'/501'/0'/0'");
  tx.sign(kp);
  const signedTxBase64 = Buffer.from(tx.serialize({ requireAllSignatures: false, verifySignatures: false })).toString("base64");
  let signature;
  try {
    signature = bs58.encode(tx.signatures[0].signature);
  } catch {}
  return { signedTxBase64, signature };
}

async function main() {
  const raw = await readAllStdin();
  const body = JSON.parse(raw || "{}");
  if (body.op !== "attach_tpsl") throw new Error(`Unsupported op: ${body.op || "<none>"}`);

  const cfg = loadConfig();
  const idl = JSON.parse(fs.readFileSync(cfg._idlFull, "utf8"));
  if (!idl || !Array.isArray(idl.instructions) || idl.instructions.length === 0) {
    throw new Error(`IDL at ${cfg._idlFull} does not look like an Anchor IDL (no instructions).`);
  }
  if (process.env.DEBUG_NATIVE === "1") {
    console.error("[DEBUG] idl.instructions", idl.instructions.length);
  }

  const params = body.params || {};
  const owner = params.owner;
  if (!owner) throw new Error("params.owner required");

  const out = await buildPerpsTriggerTx({ cfg, idl, owner, params, context: body.context || {} });

  const signed = maybeNativeSign(out.tx);
  delete out.tx;
  if (signed) {
    out.signedTxBase64 = signed.signedTxBase64;
    if (signed.signature) out.signature = signed.signature;
  }
  process.stdout.write(JSON.stringify(out));
}

main().catch((err) => {
  const msg = err && err.stack ? err.stack : String(err);
  console.error(msg);
  process.exit(1);
});
