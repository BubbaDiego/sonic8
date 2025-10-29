#!/usr/bin/env node
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import {
  Connection,
  PublicKey,
  Transaction,
  TransactionInstruction,
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
const FORCE_MANUAL = process.env.JUP_FORCE_MANUAL === "1";

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

function okPublicKey(s, label) {
  try {
    const pk = new PublicKey(s);
    if (DEBUG) console.error("[DEBUG] PublicKey OK:", label, pk.toBase58());
    return { ok: true, pk };
  } catch (e) {
    console.error(`[DEBUG] PublicKey FAIL: ${label} :: value=${JSON.stringify(s)} :: ${e}`);
    return { ok: false, error: String(e) };
  }
}

// --- helper: build keys array in IDL order, from a map of PublicKeys ---
function keysFromIdl(idl, methodName, accountsMap) {
  const ix = (idl.instructions || []).find((i) => i.name === methodName);
  if (!ix) throw new Error(`IDL has no instruction '${methodName}'`);
  const keys = [];
  const missing = [];
  for (const acc of ix.accounts) {
    const name = acc.name;
    const pk = accountsMap[name];
    if (!pk) {
      missing.push(name);
      continue;
    }
    keys.push({
      pubkey: pk instanceof PublicKey ? pk : new PublicKey(pk),
      isSigner: !!acc.isSigner,
      isWritable: !!acc.isMut,
    });
  }
  if (missing.length) {
    throw new Error(
      `Missing required Perps accounts for ${methodName}: ${missing.join(", ")}. ` +
        "Provide via PositionCore row or config.markets.<SYMBOL>",
    );
  }
  return keys;
}

// --- new helper: normalize IDL metadata to match cfg.programId ---
function normalizeIdl(idl, programIdStr) {
  const out = { ...idl, metadata: { ...(idl?.metadata || {}) } };
  const metaAddr = out.metadata.address;
  if (DEBUG) console.error("[DEBUG] idl.metadata.address (raw):", metaAddr);
  const pkMeta = okPublicKey(metaAddr, "idl.metadata.address");
  // If metadata.address missing/invalid/mismatch, force it to programId
  if (!pkMeta.ok || (programIdStr && metaAddr !== programIdStr)) {
    out.metadata.address = programIdStr;
    if (DEBUG) console.error("[DEBUG] forced idl.metadata.address ->", programIdStr);
  }
  return out;
}

function buildInstructionBuilder(program, idl, methodName, accounts, knownArgs) {
  const methodFactory = program.methods[methodName];
  if (typeof methodFactory !== "function") {
    const names = (idl.instructions || []).map((i) => i.name);
    throw new Error(
      `IDL method '${methodName}' not found. Available: ${names.join(", ")}`,
    );
  }

  const instr = (idl.instructions || []).find((i) => i.name === methodName);
  const idlArgs = (instr && Array.isArray(instr.args) ? instr.args : []) || [];

  const positionalArgs = idlArgs.map((arg) => {
    const name = arg?.name;
    if (Object.prototype.hasOwnProperty.call(knownArgs, name)) {
      return knownArgs[name];
    }

    const isOptional =
      arg &&
      arg.type &&
      typeof arg.type === "object" &&
      arg.type !== null &&
      Object.prototype.hasOwnProperty.call(arg.type, "option");

    if (isOptional) return null;

    const knownList = Object.keys(knownArgs).sort().join(", ") || "<none>";
    throw new Error(
      `Missing required arg '${name}' for ${methodName}. Provide mapping (known: ${knownList}).`,
    );
  });

  const builder = positionalArgs.length
    ? methodFactory(...positionalArgs)
    : methodFactory();

  return builder.accounts(accounts);
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

function buildTriggerKnownArgs(params, overrides = {}) {
  const isLong = !!params.isLong;
  const kindRaw = String(params.kind || "tp");
  const kindLower = kindRaw.toLowerCase();
  const above = composeTriggerAbove(isLong, params.kind);
  const entire = !!params.entirePosition;
  const triggerPrice =
    params.triggerPriceUsdAtomic !== undefined && params.triggerPriceUsdAtomic !== null
      ? bnU64(params.triggerPriceUsdAtomic)
      : null;
  const sizeUsdDelta = entire ? bnU64(0) : bnU64(params.sizeUsdDelta || 0);
  const requestType = { trigger: {} };
  const counter = randomCounter();
  const paramsArg = {
    collateralUsdDelta: bnU64(0),
    sizeUsdDelta,
    requestType,
    priceSlippage: null,
    jupiterMinimumOut: null,
    triggerPrice,
    triggerAboveThreshold: above,
    entirePosition: entire ? true : null,
    counter,
  };

  const isTp = kindLower === "tp";
  const side = isLong ? { long: {} } : { short: {} };

  const knownArgs = {
    params: paramsArg,
    paramsArg,
    request: paramsArg,
    requestParams: paramsArg,
    args: paramsArg,
    trigger: requestType,
    requestType,
    triggerPrice,
    price: triggerPrice,
    triggerAboveThreshold: above,
    above,
    triggerAbove: above,
    entirePosition: entire,
    entire,
    closeAll: entire,
    reduceOnly: entire,
    sizeUsdDelta,
    sizeUsd: sizeUsdDelta,
    sizeDelta: sizeUsdDelta,
    usdDelta: sizeUsdDelta,
    collateralUsdDelta: paramsArg.collateralUsdDelta,
    counter,
    priceSlippage: paramsArg.priceSlippage,
    jupiterMinimumOut: paramsArg.jupiterMinimumOut,
    isLong,
    side,
    isTp,
    tp: isTp,
    sl: !isTp,
    kind: kindRaw,
  };

  if (!triggerPrice) {
    knownArgs.triggerPrice = null;
    knownArgs.price = null;
  }

  Object.assign(knownArgs, overrides || {});

  return {
    knownArgs,
    paramsArg,
    requestType,
    triggerPrice,
    sizeUsdDelta,
    above,
    entire,
    isLong,
    isTp,
  };
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
  const programIdStr = cfg.programId;
  const programIdPk = new PublicKey(programIdStr); // will throw if bad
  if (DEBUG) console.error("[DEBUG] Program init — about to normalize IDL");

  const idlNorm = normalizeIdl(idl, programIdStr);

  const payerPubkey = new PublicKey(owner);
  const dummyWallet = {
    publicKey: payerPubkey,
    signTransaction: async (tx) => tx,
    signAllTransactions: async (txs) => txs,
  };
  const provider = new anchor.AnchorProvider(connection, dummyWallet, { commitment: "confirmed" });

  // Try creating Program with normalized IDL; on failure, dump context
  let program;
  try {
    program = new anchor.Program(idlNorm, programIdPk, provider);
  } catch (e) {
    console.error("[DEBUG] Program ctor failed.");
    console.error("[DEBUG] programIdPk:", programIdPk.toBase58());
    console.error("[DEBUG] idlNorm.metadata.address:", idlNorm?.metadata?.address);
    console.error("[DEBUG] idlNorm.name/version:", idlNorm?.name, idlNorm?.version);
    throw e;
  }

  if (DEBUG) console.error("[DEBUG] Program ctor OK");

  const marketKey = mapMarketSymbol(params.marketSymbol);
  const accounts = resolveAccounts(context, cfg, marketKey, programIdPk, payerPubkey);

  const overrides = {
    market: marketKey,
    marketKey,
    marketSymbol: params.marketSymbol,
    symbol: params.marketSymbol,
    owner,
    ownerPubkey: payerPubkey,
    ownerPublicKey: payerPubkey,
    payer: payerPubkey,
    payerPubkey: payerPubkey,
    payerPublicKey: payerPubkey,
  };
  const { knownArgs, paramsArg } = buildTriggerKnownArgs(params, overrides);

  // The canonical struct used for Anchor call defaults to the `params` argument
  // if the IDL expects it.
  knownArgs.params = paramsArg;
  knownArgs.paramsArg = paramsArg;

  const ixs = [];
  const cuPrice = Number(cfg.computeUnitPriceMicrolamports || 0);
  if (cuPrice > 0) {
    ixs.push(ComputeBudgetProgram.setComputeUnitPrice({ microLamports: cuPrice }));
  }

  const methodName = process.env.JUP_PERPS_METHOD_TRIGGER || cfg.methodTrigger || "createDecreasePositionRequest2";
  if (DEBUG) {
    console.error("[DEBUG] method", methodName);
    console.error("[DEBUG] args keys", Object.keys(knownArgs));
    console.error("[DEBUG] accounts", Object.keys(accounts));
  }

  const ixBuilder = buildInstructionBuilder(program, idl, methodName, accounts, knownArgs);
  const ix = await ixBuilder.instruction();
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

// --- Manual builder using BorshCoder (no new anchor.Program) ---
async function buildDecreaseTriggerTx_manual({ cfg, idl, owner, params, context }) {
  const connection = new Connection(
    process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com",
    "confirmed",
  );
  const programId = new PublicKey(cfg.programId);
  const payerPubkey = new PublicKey(owner);
  const coder = new anchor.BorshCoder(idl);

  const marketKey = mapMarketSymbol(params.marketSymbol);
  const accounts = resolveAccounts(context, cfg, marketKey, programId, payerPubkey);

  const isLong = !!params.isLong;
  const above = composeTriggerAbove(isLong, params.kind);
  const entire = !!params.entirePosition;
  const triggerPrice = params.triggerPriceUsdAtomic
    ? new anchor.BN(String(params.triggerPriceUsdAtomic))
    : null;
  const sizeUsdDelta = entire
    ? new anchor.BN("0")
    : new anchor.BN(String(params.sizeUsdDelta || 0));
  const paramsArg = {
    collateralUsdDelta: new anchor.BN("0"),
    sizeUsdDelta,
    requestType: { trigger: {} },
    priceSlippage: null,
    jupiterMinimumOut: null,
    triggerPrice,
    triggerAboveThreshold: above,
    entirePosition: entire ? true : null,
    counter: new anchor.BN(String(Date.now() % 2147483647)),
  };

  const methodName =
    process.env.JUP_PERPS_METHOD_TRIGGER || cfg.methodTrigger || "createDecreasePositionRequest2";
  if (DEBUG) {
    console.error("[DEBUG] MANUAL path using BorshCoder");
    console.error("[DEBUG] method", methodName);
  }

  let data;
  try {
    data = coder.instruction.encode(methodName, paramsArg);
  } catch (e) {
    console.error(
      "[DEBUG] coder.encode failed; method/params mismatch. method=",
      methodName,
      " params keys=",
      Object.keys(paramsArg),
    );
    throw e;
  }

  const keys = keysFromIdl(idl, methodName, {
    owner: accounts.owner,
    receivingAccount: accounts.receivingAccount,
    perpetuals: accounts.perpetuals,
    pool: accounts.pool,
    position: accounts.position,
    positionRequest: accounts.positionRequest,
    positionRequestAta: accounts.positionRequestAta,
    custody: accounts.custody,
    custodyDovesPriceAccount: accounts.custodyDovesPriceAccount,
    custodyPythnetPriceAccount: accounts.custodyPythnetPriceAccount,
    collateralCustody: accounts.collateralCustody,
    desiredMint: accounts.desiredMint,
    referral: accounts.referral,
    tokenProgram: accounts.tokenProgram,
    associatedTokenProgram: accounts.associatedTokenProgram,
    systemProgram: accounts.systemProgram,
    eventAuthority: accounts.eventAuthority,
    program: accounts.program,
  });

  const ixs = [];
  const cuPrice = Number(cfg.computeUnitPriceMicrolamports || 0);
  if (cuPrice > 0)
    ixs.push(ComputeBudgetProgram.setComputeUnitPrice({ microLamports: cuPrice }));

  const ix = new TransactionInstruction({ programId, keys, data });
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
  const overrides = {
    market: marketKey,
    marketKey,
    marketSymbol: params.marketSymbol,
    symbol: params.marketSymbol,
    owner,
    ownerPubkey: payerPubkey,
    ownerPublicKey: payerPubkey,
    payer: payerPubkey,
    payerPubkey: payerPubkey,
    payerPublicKey: payerPubkey,
  };
  const { knownArgs } = buildTriggerKnownArgs(params, overrides);
  if (DEBUG) {
    console.error("[DEBUG] fallback builder for", methodName);
    console.error("[DEBUG] known args", Object.keys(knownArgs));
  }

  const ixBuilder = buildInstructionBuilder(program, idl, methodName, accounts, knownArgs);
  const ix = await ixBuilder.instruction();

  const ixs = [];
  const cuPrice = Number(cfg.computeUnitPriceMicrolamports || 0);
  if (cuPrice > 0) {
    ixs.push(ComputeBudgetProgram.setComputeUnitPrice({ microLamports: cuPrice }));
  }
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

function finalizeAndWrite(out) {
  const signed = maybeNativeSign(out.tx);
  delete out.tx;
  if (signed) {
    out.signedTxBase64 = signed.signedTxBase64;
    if (signed.signature) out.signature = signed.signature;
  }
  process.stdout.write(JSON.stringify(out));
}

async function main() {
  const raw = await readAllStdin();
  const body = JSON.parse(raw || "{}");

  if (body.op && body.op !== "attach_tpsl") {
    throw new Error(`Unsupported op: ${body.op}`);
  }

  const cfg = loadConfig();
  const idlRaw = JSON.parse(fs.readFileSync(cfg._idlFull, "utf8"));
  if (!idlRaw || !Array.isArray(idlRaw.instructions) || idlRaw.instructions.length === 0) {
    throw new Error(`IDL at ${cfg._idlFull} does not look like an Anchor IDL (no instructions).`);
  }
  if (DEBUG) console.error("[DEBUG] idl.instructions", idlRaw.instructions.length);

  const idl = normalizeIdl(idlRaw, cfg.programId);

  const params = body.params || {};
  const owner = params.owner;
  if (!owner) throw new Error("params.owner required");

  const methodName =
    process.env.JUP_PERPS_METHOD_TRIGGER || cfg.methodTrigger || "createDecreasePositionRequest2";
  if (DEBUG) console.error("[DEBUG] using method", methodName);

  if (FORCE_MANUAL) {
    if (methodName !== "createDecreasePositionRequest2") {
      throw new Error("JUP_FORCE_MANUAL=1 only supported for createDecreasePositionRequest2");
    }
    if (DEBUG) console.error("[DEBUG] FORCE_MANUAL=1 -> using BorshCoder path only");
    const out = await buildDecreaseTriggerTx_manual({
      cfg,
      idl,
      owner,
      params,
      context: body.context || {},
    });
    finalizeAndWrite(out);
    return;
  }

  let out;
  try {
    if (methodName === "createDecreasePositionRequest2") {
      out = await buildDecreaseTriggerTx({
        cfg,
        idl,
        owner,
        params,
        context: body.context || {},
      });
    } else {
      out = await buildPerpsTriggerTx({
        cfg,
        idl,
        owner,
        params,
        context: body.context || {},
      });
    }
  } catch (e) {
    if (methodName !== "createDecreasePositionRequest2") throw e;
    if (DEBUG) {
      console.error(
        "[DEBUG] Program path failed, falling back to manual coder path:",
        e.stack || String(e),
      );
    }
    out = await buildDecreaseTriggerTx_manual({
      cfg,
      idl,
      owner,
      params,
      context: body.context || {},
    });
  }

  finalizeAndWrite(out);
}

main().catch((err) => {
  const msg = err && err.stack ? err.stack : String(err);
  console.error(msg);
  process.exit(1);
});
