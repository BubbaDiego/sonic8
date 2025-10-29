#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import {
  Connection,
  PublicKey,
  Transaction,
  ComputeBudgetProgram,
  Keypair,
  SystemProgram,
} from "@solana/web3.js";
import * as anchor from "@coral-xyz/anchor";
import {
  getAssociatedTokenAddressSync,
  TOKEN_PROGRAM_ID,
  ASSOCIATED_TOKEN_PROGRAM_ID,
} from "@solana/spl-token";
import bs58 from "bs58";
import * as bip39 from "bip39";
import { derivePath as ed25519DerivePath } from "ed25519-hd-key";
import nacl from "tweetnacl";

const DEBUG = process.env.DEBUG_NATIVE === "1";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ---------- utils ----------
function readAllStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => {
      data += c;
    });
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
    } catch {
      // ignore copy failures, loadConfig will surface the missing file
    }
  }
  return cfg;
}

function loadConfig() {
  const cfgPath = ensureConfigPath();
  if (!fs.existsSync(cfgPath)) {
    throw new Error(
      `Missing ${cfgPath}. Copy config.example.json to config.json and fill values.`,
    );
  }
  const j = JSON.parse(fs.readFileSync(cfgPath, "utf8"));

  if (process.env.JUP_PERPS_PROGRAM_ID) j.programId = process.env.JUP_PERPS_PROGRAM_ID;
  if (process.env.JUP_PERPS_IDL) j.idlPath = process.env.JUP_PERPS_IDL;
  if (process.env.JUP_PERPS_METHOD_TRIGGER) j.methodTrigger = process.env.JUP_PERPS_METHOD_TRIGGER;
  if (process.env.JUP_PERPS_MICROLAMPORTS) {
    j.computeUnitPriceMicrolamports = Number(process.env.JUP_PERPS_MICROLAMPORTS);
  }

  if (!j.idlPath) throw new Error("config.idlPath is required");
  j._idlFull = path.isAbsolute(j.idlPath) ? j.idlPath : path.join(__dirname, j.idlPath);
  if (!fs.existsSync(j._idlFull)) throw new Error(`IDL not found at ${j._idlFull}`);
  if (!j.programId) {
    // Fallback to IDL metadata address if present
    const idlProbe = JSON.parse(fs.readFileSync(j._idlFull, "utf8"));
    const metaAddr = idlProbe?.metadata?.address;
    if (metaAddr && typeof metaAddr === "string") j.programId = metaAddr;
  }
  if (!j.programId)
    throw new Error("config.programId is empty and IDL has no metadata.address");

  if (DEBUG) {
    console.error("[DEBUG] programId", j.programId);
    console.error("[DEBUG] idlPath", j._idlFull);
    console.error("[DEBUG] methodTrigger", j.methodTrigger || process.env.JUP_PERPS_METHOD_TRIGGER);
  }
  return j;
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

function deriveEventAuthority(programId) {
  return PublicKey.findProgramAddressSync([Buffer.from("__event_authority")], programId)[0];
}

function ensurePubkey(v, name) {
  if (!v) throw new Error(`Missing ${name}`);
  return v instanceof PublicKey ? v : new PublicKey(v);
}

function pickDesiredMint(context, cfg, marketKey) {
  const row = (context && context.positionRow) || {};
  return (
    row.desiredMint ||
    (cfg.markets && cfg.markets[marketKey] && cfg.markets[marketKey].desiredMint) ||
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
  );
}

// ---------- build Decrease (Trigger) ----------
function composeTriggerAbove(isLong, kind) {
  const k = String(kind || "tp").toLowerCase();
  return isLong ? k === "tp" : k !== "tp";
}

function bnU64(x) {
  return new anchor.BN(String(x ?? 0));
}

function randomCounter() {
  const n = BigInt(Date.now()) * 1000n + BigInt(Math.floor(Math.random() * 1000));
  return new anchor.BN(n.toString());
}

function resolveAccounts(context, cfg, marketKey, programId, payerPubkey) {
  const row = (context && context.positionRow) || {};
  const a = {};

  a.perpetuals = row.perpetuals || row.group || null;
  a.pool = row.pool || (cfg.markets?.[marketKey]?.pool || null);
  a.position = row.position || row.position_account || null;
  a.positionRequest = row.positionRequest || null;
  a.custody = row.custody || null;
  a.collateralCustody = row.collateralCustody || row.collateral_custody || null;
  a.custodyDovesPriceAccount = row.custodyDovesPriceAccount || null;
  a.custodyPythnetPriceAccount = row.custodyPythnetPriceAccount || null;

  a.desiredMint = pickDesiredMint(context, cfg, marketKey);
  const desiredMintPk = ensurePubkey(a.desiredMint, "desiredMint");
  a.receivingAccount = getAssociatedTokenAddressSync(
    desiredMintPk,
    payerPubkey,
    false,
    TOKEN_PROGRAM_ID,
    ASSOCIATED_TOKEN_PROGRAM_ID,
  );

  if (!a.positionRequest) {
    a.positionRequest = cfg.markets?.[marketKey]?.positionRequest || null;
  }

  if (a.positionRequest) {
    const posReqPk = ensurePubkey(a.positionRequest, "positionRequest");
    a.positionRequestAta = getAssociatedTokenAddressSync(
      desiredMintPk,
      posReqPk,
      true,
      TOKEN_PROGRAM_ID,
      ASSOCIATED_TOKEN_PROGRAM_ID,
    );
  }

  a.eventAuthority = deriveEventAuthority(programId);

  a.tokenProgram = TOKEN_PROGRAM_ID;
  a.associatedTokenProgram = ASSOCIATED_TOKEN_PROGRAM_ID;
  a.systemProgram = SystemProgram.programId;

  const required = [
    "perpetuals",
    "pool",
    "position",
    "positionRequest",
    "positionRequestAta",
    "custody",
    "collateralCustody",
    "desiredMint",
    "receivingAccount",
    "eventAuthority",
  ];
  const missing = required.filter((k) => !a[k]);
  if (missing.length) {
    throw new Error(
      "Missing required Perps accounts: " +
        missing.join(", ") +
        ". Provide them via PositionCore row or config.markets." +
        marketKey,
    );
  }

  return {
    owner: payerPubkey,
    receivingAccount: ensurePubkey(a.receivingAccount, "receivingAccount"),
    perpetuals: ensurePubkey(a.perpetuals, "perpetuals"),
    pool: ensurePubkey(a.pool, "pool"),
    position: ensurePubkey(a.position, "position"),
    positionRequest: ensurePubkey(a.positionRequest, "positionRequest"),
    positionRequestAta: ensurePubkey(a.positionRequestAta, "positionRequestAta"),
    custody: ensurePubkey(a.custody, "custody"),
    custodyDovesPriceAccount: a.custodyDovesPriceAccount
      ? ensurePubkey(a.custodyDovesPriceAccount, "custodyDovesPriceAccount")
      : ensurePubkey(a.custody, "custody"),
    custodyPythnetPriceAccount: a.custodyPythnetPriceAccount
      ? ensurePubkey(a.custodyPythnetPriceAccount, "custodyPythnetPriceAccount")
      : ensurePubkey(a.custody, "custody"),
    collateralCustody: ensurePubkey(a.collateralCustody, "collateralCustody"),
    desiredMint: desiredMintPk,
    referral: new PublicKey("11111111111111111111111111111111"),
    tokenProgram: TOKEN_PROGRAM_ID,
    associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
    systemProgram: SystemProgram.programId,
    eventAuthority: a.eventAuthority,
    program: programId,
  };
}

async function buildDecreaseTriggerTx({ cfg, idl, owner, params, context }) {
  const connection = new Connection(
    process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com",
    "confirmed",
  );
  const programId = new PublicKey(cfg.programId); // if this line still fails, cfg.programId is actually undefined or bad
  if (DEBUG) console.error("[DEBUG] PublicKey(programId) ok");
  const payerPubkey = new PublicKey(owner);

  const dummyWallet = {
    publicKey: payerPubkey,
    signTransaction: async (tx) => tx,
    signAllTransactions: async (txs) => txs,
  };
  const provider = new anchor.AnchorProvider(connection, dummyWallet, { commitment: "confirmed" });
  const program = new anchor.Program(idl, programId, provider);

  const marketKey = mapMarketSymbol(params.marketSymbol);
  const accounts = resolveAccounts(context, cfg, marketKey, programId, payerPubkey);

  const isLong = !!params.isLong;
  const above = composeTriggerAbove(isLong, params.kind);
  const entire = !!params.entirePosition;
  const triggerPrice = params.triggerPriceUsdAtomic ? bnU64(params.triggerPriceUsdAtomic) : null;
  const sizeUsdDelta = entire ? bnU64(0) : bnU64(params.sizeUsdDelta || 0);
  const requestType = { trigger: {} };

  const paramsArg = {
    collateralUsdDelta: bnU64(0),
    sizeUsdDelta,
    requestType,
    priceSlippage: null,
    jupiterMinimumOut: null,
    triggerPrice,
    triggerAboveThreshold: above,
    entirePosition: entire ? true : null,
    counter: randomCounter(),
  };

  const ixs = [];
  const cuPrice = Number(cfg.computeUnitPriceMicrolamports || 0);
  if (cuPrice > 0) {
    ixs.push(ComputeBudgetProgram.setComputeUnitPrice({ microLamports: cuPrice }));
  }

  const methodName = process.env.JUP_PERPS_METHOD_TRIGGER || cfg.methodTrigger || "createDecreasePositionRequest2";
  if (DEBUG) {
    console.error("[DEBUG] method", methodName);
    console.error("[DEBUG] args keys", Object.keys(paramsArg));
    console.error("[DEBUG] accounts", Object.keys(accounts));
  }

  const methodFactory = program.methods[methodName];
  if (typeof methodFactory !== "function") {
    throw new Error(
      `IDL method '${methodName}' not found. Set config.methodTrigger or JUP_PERPS_METHOD_TRIGGER.`,
    );
  }
  const ixBuilder = paramsArg ? methodFactory(paramsArg) : methodFactory();
  const ix = await ixBuilder.accounts(accounts).instruction();
  ixs.push(ix);

  const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash("finalized");
  const tx = new Transaction({ feePayer: payerPubkey, recentBlockhash: blockhash }).add(...ixs);
  const unsignedTxBase64 = Buffer.from(
    tx.serialize({ requireAllSignatures: false, verifySignatures: false }),
  ).toString("base64");
  return {
    unsignedTxBase64,
    requestPda: accounts.positionRequest.toBase58(),
    blockhash,
    lastValidBlockHeight,
    tx,
  };
}

// existing helpers (memo/ultra) kept; route by method
async function buildPerpsTriggerTx({ cfg, idl, owner, params, context }) {
  const connection = new Connection(
    process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com",
    "confirmed",
  );
  const programId = new PublicKey(cfg.programId);
  const payerPubkey = new PublicKey(owner);

  const dummyWallet = {
    publicKey: payerPubkey,
    signTransaction: async (tx) => tx,
    signAllTransactions: async (txs) => txs,
  };
  const provider = new anchor.AnchorProvider(connection, dummyWallet, { commitment: "confirmed" });
  const program = new anchor.Program(idl, programId, provider);

  const methodName = process.env.JUP_PERPS_METHOD_TRIGGER || cfg.methodTrigger;
  if (typeof program.methods[methodName] !== "function") {
    throw new Error(`IDL method '${methodName}' not found in fallback path.`);
  }
  throw new Error(
    `Instruction '${methodName}' requires specialized mapping. Use createDecreasePositionRequest2 for Trigger TP/SL.`,
  );
}

function findSignerTxt() {
  const envPath = process.env.SIGNER_PATH;
  if (envPath && fs.existsSync(envPath)) return envPath;
  const candidate = path.join(process.cwd(), "signer.txt");
  if (fs.existsSync(candidate)) return candidate;
  return null;
}

function maybeNativeSign(tx) {
  if (process.env.NATIVE_SIGNER !== "1") return null;
  const signerPath = findSignerTxt();
  if (!signerPath)
    throw new Error(
      "NATIVE_SIGNER=1 but signer.txt not found (set SIGNER_PATH or place at repo root)",
    );
  const { mnemonic, bip39Passphrase } = parseSignerFile(signerPath);
  const kp = keypairFromMnemonic(
    mnemonic,
    bip39Passphrase,
    process.env.SOLANA_DERIVATION_PATH || "m/44'/501'/0'/0'",
  );
  tx.sign(kp);
  const signedTxBase64 = Buffer.from(
    tx.serialize({ requireAllSignatures: false, verifySignatures: false }),
  ).toString("base64");
  let signature;
  try {
    signature = bs58.encode(tx.signatures[0].signature);
  } catch {
    // ignore signature extraction errors
  }
  return { signedTxBase64, signature };
}

async function main() {
  const raw = await readAllStdin();
  const body = JSON.parse(raw || "{}");

  if (body.op && body.op !== "attach_tpsl") {
    throw new Error(`Unsupported op: ${body.op}`);
  }

  const cfg = loadConfig();
  const idl = JSON.parse(fs.readFileSync(cfg._idlFull, "utf8"));
  if (!idl || !Array.isArray(idl.instructions) || idl.instructions.length === 0) {
    throw new Error(`IDL at ${cfg._idlFull} does not look like an Anchor IDL (no instructions).`);
  }
  if (DEBUG) console.error("[DEBUG] idl.instructions", idl.instructions.length);

  const params = body.params || {};
  const owner = params.owner;
  if (!owner) throw new Error("params.owner required");

  const methodName = process.env.JUP_PERPS_METHOD_TRIGGER || cfg.methodTrigger || "createDecreasePositionRequest2";

  let out;
  if (methodName === "createDecreasePositionRequest2") {
    out = await buildDecreaseTriggerTx({ cfg, idl, owner, params, context: body.context || {} });
  } else {
    out = await buildPerpsTriggerTx({ cfg, idl, owner, params, context: body.context || {} });
  }

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
