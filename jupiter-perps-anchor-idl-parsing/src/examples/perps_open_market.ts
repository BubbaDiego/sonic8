/* Open/Increase position at market, with optional collateral deposit */
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import {
  AnchorProvider,
  Program,
  Wallet,
  setProvider,
  type Idl,
} from "@coral-xyz/anchor";
import * as web3 from "@solana/web3.js";
import {
  PublicKey,
  SystemProgram,
  Keypair,
  VersionedTransaction,
  TransactionMessage,
  ComputeBudgetProgram,
} from "@solana/web3.js";
import {
  getAssociatedTokenAddressSync,
  createAssociatedTokenAccountIdempotentInstruction,
  TOKEN_PROGRAM_ID,
  ASSOCIATED_TOKEN_PROGRAM_ID,
} from "@solana/spl-token";
import { RpcPool } from "../lib/rpc_failover.js";
import { bar, info, kv, ok, fail } from "../utils/logger.js";
import * as cfg from "../config/perps.js";
import {
  toMicroUsd,
  toTokenAmount,
  derivePdaFromIdl,
  derivePositionPdaPoolFirst,
  derivePositionPdaOwnerFirst,
  derivePositionForIdlOrder,
  derivePositionForSwappedOrder,
  sideToEnum,
} from "../utils/resolve.js";
import { IDL as JUP_PERPS_IDL } from "../idl/jupiter-perpetuals-idl.js";
import { toPk } from "../utils/pk.js";
import {
  createAtaIxStrict,
  deriveAtaStrict,
  detectTokenProgramForMint,
} from "../utils/ata.js";

async function makeProviderAndProgram(
  conn: web3.Connection,
  wallet: Wallet,
  idl: Idl,
  programId: web3.PublicKey,
) {
  const provider = new AnchorProvider(conn, wallet, {
    commitment: "confirmed",
  });
  setProvider(provider);
  const program = new Program(idl, programId, provider);
  return { provider, program };
}

type CustodyInfo = {
  pubkey: web3.PublicKey;
  account: any;
  mint: web3.PublicKey;
};

function pickCustodyByMint(custodies: CustodyInfo[], mint: web3.PublicKey) {
  const c = custodies.find((x) => x.mint.equals(mint));
  if (!c) throw new Error(`No custody found for mint ${mint.toBase58()}`);
  return c.pubkey;
}

// Collect logs from both web3 and Anchor error shapes
function collectAllLogLines(err: any): string[] {
  const a: string[] = Array.isArray(err?.transactionLogs)
    ? err.transactionLogs
    : [];
  const b: string[] = Array.isArray(err?.logs) ? err.logs : [];
  const c: string[] = Array.isArray(err?.errorLogs) ? err.errorLogs : [];
  return [...a, ...b, ...c].filter((x) => typeof x === "string");
}

// Parse "Invalid collateral account" Left/Right pubkeys
function parseInvalidCollateralFromLogs(
  logs: string[],
): { left: string; right: string } | null {
  const base58 = /[1-9A-HJ-NP-Za-km-z]{32,44}/;
  const i = logs.findIndex((l) => l.includes("Invalid collateral account"));
  if (i < 0) return null;
  const window = logs.slice(i, i + 10);
  const left = window.find((l) => l.includes("Left"))?.match(base58)?.[0];
  const right = window.find((l) => l.includes("Right"))?.match(base58)?.[0];
  return left && right ? { left, right } : null;
}

function shouldSwapCustodiesForIdlMismatch(
  logs: string[] | undefined,
  marketCustodyPk: web3.PublicKey,
  collateralCustodyPk: web3.PublicKey,
): boolean {
  if (!logs?.length) return false;
  const p = parseInvalidCollateralFromLogs(logs);
  return (
    !!p &&
    p.left === marketCustodyPk.toBase58() &&
    p.right === collateralCustodyPk.toBase58()
  );
}

// Parse the expected 'Right:' pubkey for ConstraintSeeds on a specific account
function parseConstraintSeedsRight(logs: string[], accountName: string): string | null {
  const base58 = /[1-9A-HJ-NP-Za-km-z]{32,44}/;
  const idx = logs.findIndex(
    (l) => l.includes("ConstraintSeeds") && l.includes(`account: ${accountName}`),
  );
  if (idx < 0) return null;
  const window = logs.slice(idx, idx + 12);
  return window.find((l) => l.includes("Right"))?.match(base58)?.[0] ?? null;
}

function makePositionUsdcAtaIx(
  payer: web3.PublicKey,
  positionPk: web3.PublicKey,
  usdcMint: web3.PublicKey,
) {
  const ata = getAssociatedTokenAddressSync(usdcMint, positionPk, true);
  const ix = createAssociatedTokenAccountIdempotentInstruction(
    payer,
    ata,
    positionPk,
    usdcMint,
  );
  return { ata, ix };
}

// Pretty-printer for the final compiled instruction → accounts
async function debugPrintIx(program: Program, m: any, label: string) {
  const ix = await m.instruction();
  const idlIx = program.idl.instructions.find(
    (i: any) => i.name === "createIncreasePositionMarketRequest",
  );
  console.log(`🔎 Final ix accounts (${label}) (IDL name → pubkey):`);
  ix.keys.forEach((k: web3.AccountMeta, i: number) => {
    const name = idlIx?.accounts?.[i]?.name ?? `idx_${i}`;
    console.log(`${String(i).padStart(2)} ${name} → ${k.pubkey.toBase58()}`);
  });
  return ix;
}

// Build accounts with selectable mapping mode
function buildIncreaseAccounts(
  args: {
    owner: web3.PublicKey;
    perpetualsPk: web3.PublicKey;
    poolPk: web3.PublicKey;
    positionPk: web3.PublicKey;
    positionRequestPk: web3.PublicKey;
    positionRequestUsdcAta: web3.PublicKey;
    ownerUsdcAta: web3.PublicKey;
    marketCustodyPk: web3.PublicKey;
    collateralCustodyPk: web3.PublicKey;
    collateralMintPk: web3.PublicKey;
    referralOrSystemProgram: web3.PublicKey;
    eventAuthorityPk: web3.PublicKey;
    perpsProgramId: web3.PublicKey;
  },
  mode: "idl" | "swapped" = "idl",
) {
  const custody =
    mode === "idl" ? args.marketCustodyPk : args.collateralCustodyPk;
  const collateralCustody =
    mode === "idl" ? args.collateralCustodyPk : args.marketCustodyPk;

  const accounts = {
    owner: args.owner,
    fundingAccount: args.ownerUsdcAta,
    perpetuals: args.perpetualsPk,
    pool: args.poolPk,
    position: args.positionPk,
    positionRequest: args.positionRequestPk,
    positionRequestAta: args.positionRequestUsdcAta,
    custody,
    collateralCustody,
    inputMint: args.collateralMintPk,
    referral: args.referralOrSystemProgram,
    tokenProgram: TOKEN_PROGRAM_ID,
    associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
    systemProgram: web3.SystemProgram.programId,
    eventAuthority: args.eventAuthorityPk,
    program: args.perpsProgramId,
  };

  if (accounts.custody.equals(accounts.collateralCustody)) {
    throw new Error("custody == collateralCustody (should never happen)");
  }
  return accounts;
}

async function sendIncreasePositionWithSwapRetry(params: {
  program: Program;
  preIxs: web3.TransactionInstruction[];
  postIxs: web3.TransactionInstruction[];
  ixArgs: any;
  payer: web3.PublicKey;
  owner: web3.PublicKey;
  perpetualsPk: web3.PublicKey;
  poolPk: web3.PublicKey;
  positionPk: web3.PublicKey;
  positionRequestPk: web3.PublicKey;
  positionRequestUsdcAta: web3.PublicKey;
  ownerUsdcAta: web3.PublicKey;
  marketCustodyPk: web3.PublicKey;
  collateralCustodyPk: web3.PublicKey;
  collateralMintPk: web3.PublicKey;
  referralOrSystemProgram: web3.PublicKey;
  eventAuthorityPk: web3.PublicKey;
  perpsProgramId: web3.PublicKey;
}) {
  const {
    program,
    ixArgs,
    payer,
    collateralMintPk,
    owner,
    perpetualsPk,
    poolPk,
    positionRequestPk,
    positionRequestUsdcAta,
    ownerUsdcAta,
    referralOrSystemProgram,
    eventAuthorityPk,
    perpsProgramId,
  } = params;

  let mode: "idl" | "swapped" = "idl";
  let positionPk = params.positionPk;
  let preIxs = [...params.preIxs];
  let postIxs = [...params.postIxs];

  const buildAccounts = () => ({
    owner,
    fundingAccount: ownerUsdcAta,
    perpetuals: perpetualsPk,
    pool: poolPk,
    position: positionPk,
    positionRequest: positionRequestPk,
    positionRequestAta: positionRequestUsdcAta,
    custody: mode === "idl" ? params.marketCustodyPk : params.collateralCustodyPk,
    collateralCustody:
      mode === "idl" ? params.collateralCustodyPk : params.marketCustodyPk,
    inputMint: params.collateralMintPk,
    referral: referralOrSystemProgram,
    tokenProgram: TOKEN_PROGRAM_ID,
    associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
    systemProgram: web3.SystemProgram.programId,
    eventAuthority: eventAuthorityPk,
    program: perpsProgramId,
  });

  async function sendOnce(label: string) {
    const method = (program as any).methods
      .createIncreasePositionMarketRequest(ixArgs)
      .accountsStrict(buildAccounts())
      .preInstructions(preIxs)
      .postInstructions(postIxs);

    await debugPrintIx(program as Program, method, label);
    await method.rpc();
  }

  try {
    await sendOnce("attempt 1/3 (idl)");
    return;
  } catch (e: any) {
    const logs = collectAllLogLines(e);
    const code = e?.error?.errorCode?.number ?? e?.errorCode?.number ?? null;

    if (
      code === 6006 ||
      shouldSwapCustodiesForIdlMismatch(
        logs,
        params.marketCustodyPk,
        params.collateralCustodyPk,
      )
    ) {
      console.warn("🔁 6006 detected → switching to swapped custody order");
      mode = "swapped";
      positionPk = derivePositionForSwappedOrder(
        owner,
        poolPk,
        params.marketCustodyPk,
        params.collateralCustodyPk,
        perpsProgramId,
      );
      preIxs = [...params.preIxs];
    } else {
      throw e;
    }
  }

  try {
    await sendOnce("attempt 2/3 (swapped)");
    return;
  } catch (e: any) {
    const logs = collectAllLogLines(e);
    const code = e?.error?.errorCode?.number ?? e?.errorCode?.number ?? null;

    if (code !== 2006) throw e;

    const right = parseConstraintSeedsRight(logs, "position");
    if (!right) throw e;
    positionPk = new web3.PublicKey(right);
    console.warn("🔧 Aligning position PDA from logs →", right);

    const { ix: posAtaIx } = makePositionUsdcAtaIx(
      payer,
      positionPk,
      collateralMintPk,
    );
    preIxs = [...params.preIxs, posAtaIx];
  }

  await sendOnce("attempt 3/3 (swapped + position fix)");
}

function shortId(s: string) {
  return s.length > 10 ? `${s.slice(0, 4)}…${s.slice(-4)}` : s;
}
function labelFor(programId: string) {
  return programId === "ComputeBudget111111111111111111111111111111"
    ? "ComputeBudget"
    : programId === "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
      ? "AssociatedToken"
      : programId === "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        ? "Token"
        : programId === "11111111111111111111111111111111"
          ? "System"
          : programId === "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu"
            ? "Perps"
            : shortId(programId);
}
function formatLogs(raw: string[]): string[] {
  // squash repetitive AToken “CreateIdempotent” chatter and Token size/init chatter
  const skip = [
    "Instruction: GetAccountDataSize",
    "return: TokenkegQfe",
    "Please upgrade to SPL Token 2022 for immutable owner support",
    "Instruction: InitializeAccount3",
  ];
  const out: string[] = [];
  for (const l of raw || []) {
    if (skip.some((k) => l.includes(k))) continue;
    // Prefix with a label if the line starts with “Program <pid>” or “Program log: …”
    const m = l.match(/^Program\s+([A-Za-z0-9]+)\s.*|^Program log:\s(.*)$/);
    if (m) {
      // keep as-is but compact the pid into a label when present
      const pid = l.match(/^Program\s+([A-Za-z0-9]+)/)?.[1] ?? "";
      if (pid)
        out.push(
          `• ${labelFor(pid)} → ${l.replace(/^Program\s+[A-Za-z0-9]+\s/, "")}`,
        );
      else out.push(`• ${l.replace(/^Program log:\s/, "")}`);
    } else {
      out.push(l);
    }
  }
  // collapse duplicate consecutive lines
  return out.filter((v, i, a) => i === 0 || v !== a[i - 1]);
}

(async () => {
  const argv = await yargs(hideBin(process.argv))
    .option("rpc", { type: "string", demandOption: true })
    .option("kp", {
      type: "string",
      demandOption: true,
      describe: "Path to keypair JSON/base58",
    })
    .option("rpc-fallbacks", {
      type: "string",
      describe: "Comma-separated fallback RPC endpoints",
    })
    .option("market", {
      type: "string",
      choices: ["SOL", "ETH", "BTC"] as const,
      demandOption: true,
    })
    .option("side", {
      type: "string",
      choices: ["long", "short"] as const,
      demandOption: true,
    })
    .option("size-usd", {
      type: "number",
      demandOption: true,
      describe: "USD notional for size",
    })
    .option("collat", {
      type: "number",
      default: 0,
      describe: "Collateral token amount (UI units)",
    })
    .option("collat-mint", {
      type: "string",
      describe:
        "Override collateral mint (default: WSOL for long, USDC for short)",
    })
    .option("position", {
      type: "string",
      describe: "Override Position PDA (use the Right: value from logs)",
    })
    .option("position-request", {
      type: "string",
      describe: "Override PositionRequest PDA (use Perps 'Right:' value)",
    })
    .option("oracle-price", {
      type: "number",
      describe: "Oracle/mark price in USD for guardrail calc",
    })
    .option("slip", {
      type: "number",
      describe: "Slippage fraction for guardrail (e.g., 0.02)",
    })
    .option("max-price", {
      type: "number",
      describe: "Explicit max price (LONG)",
    })
    .option("min-price", {
      type: "number",
      describe: "Explicit min price (SHORT)",
    })
    .option("dry-run", { type: "boolean", default: false })
    .option("flip-custody-order", {
      type: "boolean",
      default: false,
      describe: "Force custody↔collateralCustody order swap (diagnostics)",
    })
    .option("cu-limit", {
      type: "number",
      default: 800_000,
      describe: "Compute unit limit to request for the transaction",
    })
    .option("priority-microlamports", {
      type: "number",
      default: 100_000,
      describe: "Micro-lamports to pay per compute unit for priority fees",
    })
    .strict()
    .parse();

  const rpc = argv.rpc as string;
  const rpcFallbacksCsv =
    (argv["rpc-fallbacks"] as string | undefined) ??
    process.env.SONIC_SOLANA_RPC_FALLBACKS ??
    "";

  const rpcPool = new RpcPool(rpc, rpcFallbacksCsv, {
    perEndpointMaxRetries: 5,
    baseDelayMs: 500,
    maxDelayMs: 15000,
  });

  const idl = JUP_PERPS_IDL as Idl;
  const meta = (idl as any)?.metadata;
  const programId = new PublicKey(
    meta?.address ??
      (() => {
        throw new Error("IDL.metadata.address missing; update IDL");
      })(),
  );

  const kp = cfg.loadKeypair(argv.kp);
  const wallet = new Wallet(kp);

  const endpointFor = (conn: web3.Connection) =>
    (conn as any).rpcEndpoint ??
    (conn as any)._rpcEndpoint ??
    rpcPool.currentEndpoint();

  let provider!: AnchorProvider;
  let program!: Program<any>;
  let currentEndpoint = "";
  const owner = wallet.payer as Keypair;

  async function ensureProviderOnConnection(conn: web3.Connection) {
    const endpoint = endpointFor(conn);
    if (!provider || currentEndpoint !== endpoint) {
      const built = await makeProviderAndProgram(conn, wallet, idl, programId);
      provider = built.provider;
      program = built.program as Program<any>;
      currentEndpoint = endpoint;
    }
  }

  bar("Bootstrap", "🔗");

  let perpetuals!: { publicKey: PublicKey; account: any };
  let pool!: { publicKey: PublicKey; account: any };
  let allCustodies: CustodyInfo[] = [];
  let bootstrapLogged = false;

  await rpcPool.runWithFailover(async (conn) => {
    await ensureProviderOnConnection(conn);
    const endpoint = endpointFor(conn);
    if (!bootstrapLogged) {
      info("🧭", `Network: ${endpoint}`);
      kv("Owner", wallet.publicKey.toBase58());
      kv("Program", programId.toBase58());
      ok("IDL loaded and program ready");
      bootstrapLogged = true;
    }

    perpetuals = await cfg.getSingletonPerpetuals(program);
    pool = await cfg.getSingletonPool(program);
    const allCustodiesRaw = await cfg.getCustodies(program, pool.account);
    allCustodies = allCustodiesRaw.map((c) => ({
      ...c,
      mint: new PublicKey(c.account.mint as PublicKey),
    }));
    return true;
  }, "bootstrap/perps+pool+custodies");

  const ix = program.idl?.instructions?.find(
    (i: any) => i.name === "createIncreasePositionMarketRequest",
  );
  console.log(
    "IDL accounts:",
    ix?.accounts.map((a: any) => a.name),
  );

  const marketMint = (cfg.MINTS as any)[argv.market] as PublicKey;
  const sideEnum = sideToEnum(argv.side);
  const flipCustodyOrder = argv["flip-custody-order"] === true;

  const marketCustodyPk = pickCustodyByMint(allCustodies, marketMint);
  const defaultCollat = argv.side === "long" ? marketMint : cfg.MINTS.USDC;
  const collatMintArg = (argv["collat-mint"] as unknown) ?? null;
  const collateralMint = collatMintArg
    ? toPk("collat-mint", collatMintArg)
    : defaultCollat;
  let collateralCustodyPk = pickCustodyByMint(allCustodies, collateralMint);
  let collateralCustodyInfo = allCustodies.find((c) =>
    c.pubkey.equals(collateralCustodyPk),
  );
  if (!collateralCustodyInfo)
    throw new Error("Unable to resolve collateral custody info");
  console.log(
    "🔑  Mints :: marketMint=",
    (marketMint as any).toBase58?.() ?? String(marketMint),
    " collateralMint=",
    (collateralMint as any).toBase58?.() ?? String(collateralMint),
  );
  console.log("🧪 custody (market):     ", marketCustodyPk.toBase58());
  console.log("🧪 collateralCustody:  ", collateralCustodyPk.toBase58());
  console.log("🧪 inputMint:          ", collateralMint.toBase58());

  bar("PDAs", "🧩");
  const positionCanonical = derivePositionForIdlOrder(
    wallet.publicKey,
    pool.publicKey,
    marketCustodyPk,
    collateralCustodyPk,
    programId,
  );
  let position: PublicKey;
  if (argv.position) {
    position = toPk("position", argv.position);
    console.log("🧩 position (override) =", position.toBase58());
  } else {
    position = positionCanonical;
    console.log("🧩 position =", position.toBase58());
  }
  const [posPoolFirst] = derivePositionPdaPoolFirst(
    programId,
    pool.publicKey,
    wallet.publicKey,
  );
  const [posOwnerFirst] = derivePositionPdaOwnerFirst(
    programId,
    wallet.publicKey,
    pool.publicKey,
  );

  // Loud, one-time debug to compare with Perps' "Right:" if it error-logs again
  console.log(
    "🧩 position PDAs :: canonical=",
    positionCanonical.toBase58(),
    " poolFirst=",
    posPoolFirst.toBase58(),
    " ownerFirst=",
    posOwnerFirst.toBase58(),
  );

  // Use the canonical PDA for the request unless overridden
  const unique = Math.floor(Date.now() / 1000);
  let positionRequest: PublicKey;
  const prOverride = argv["position-request"] as string | undefined;
  const havePR = !!prOverride;
  if (havePR) {
    positionRequest = toPk("position-request", prOverride);
    console.log("🧩 positionRequest (override) =", positionRequest.toBase58());
  } else {
    const [derivedPositionRequest] = derivePdaFromIdl(
      JUP_PERPS_IDL as Idl,
      programId,
      "positionRequest",
      {
        owner: wallet.publicKey,
        pool: pool.publicKey,
        custody: marketCustodyPk,
        collateralCustody: collateralCustodyPk,
        seed: unique,
        position,
      },
    );
    positionRequest = derivedPositionRequest;
  }
  kv("Position", position.toBase58());
  kv("PosRequest", positionRequest.toBase58());

  const decimals = (collateralCustodyInfo.account.decimals as number) ?? 9;
  // Discovery run = no token transfer → set collat=0 on the wire when !havePR
  const sizeUsdDeltaDisc = toMicroUsd(argv["size-usd"]);
  const collateralTokenDelta = havePR
    ? toTokenAmount(argv.collat, decimals)
    : new cfg.BN(0); // discovery → 0 on-chain

  // Step 2 — Funding (owner ATA) & escrow ATAs (position request + position)
  const usdcMint = new PublicKey(
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  );
  const wsolMint = new PublicKey("So11111111111111111111111111111111111111112");

  const usdcProgramId = await detectTokenProgramForMint(
    provider.connection,
    usdcMint,
  );
  const wsolProgramId = await detectTokenProgramForMint(
    provider.connection,
    wsolMint,
  );

  const tokenProgramCache = new Map<string, PublicKey>();
  tokenProgramCache.set(usdcMint.toBase58(), usdcProgramId);
  tokenProgramCache.set(wsolMint.toBase58(), wsolProgramId);

  const mintLabel = (mint: PublicKey) => {
    if (mint.equals(usdcMint)) return "USDC";
    if (mint.equals(wsolMint)) return "WSOL";
    return mint.toBase58();
  };

  const getTokenProgramIdForMint = async (mint: PublicKey) => {
    const key = mint.toBase58();
    const cached = tokenProgramCache.get(key);
    if (cached) return cached;
    const detected = await detectTokenProgramForMint(provider.connection, mint);
    const resolved = detected ?? TOKEN_PROGRAM_ID;
    tokenProgramCache.set(key, resolved);
    return resolved;
  };

  const ownerTokenProgramId = await getTokenProgramIdForMint(collateralMint);
  const ownerAtaInit = createAtaIxStrict(
    wallet.publicKey,
    collateralMint,
    wallet.publicKey,
    /*allowOwnerOffCurve=*/ false,
    ownerTokenProgramId,
  );
  console.log(`🧪 ATA debug (${mintLabel(collateralMint)}, wallet):`, {
    mint: shortId(collateralMint.toBase58()),
    owner: shortId(wallet.publicKey.toBase58()),
    allowOwnerOffCurve: false,
    tokenProgramId: shortId(ownerTokenProgramId.toBase58()),
    ata: shortId(ownerAtaInit.ata.toBase58()),
  });
  const expectedOwnerAta = deriveAtaStrict(
    collateralMint,
    wallet.publicKey,
    false,
    ownerTokenProgramId,
  );
  if (!ownerAtaInit.ata.equals(expectedOwnerAta)) {
    throw new Error("ATA mismatch (wallet) vs seed derivation");
  }

  // Step 3 — Amounts & guardrail
  let priceGuard: cfg.BN | null = null;
  if (
    typeof argv["oracle-price"] === "number" &&
    typeof argv["slip"] === "number"
  ) {
    const factor = argv.side === "long" ? 1 + argv.slip : 1 - argv.slip;
    priceGuard = toMicroUsd(argv["oracle-price"] * factor);
  } else if (typeof argv["max-price"] === "number" && argv.side === "long") {
    priceGuard = toMicroUsd(argv["max-price"]);
  } else if (typeof argv["min-price"] === "number" && argv.side === "short") {
    priceGuard = toMicroUsd(argv["min-price"]);
  }
  if (!priceGuard) {
    fail(
      "No price guardrail provided. Use --oracle-price + --slip or --max-price/--min-price.",
    );
    process.exit(1);
  }

  bar("Amounts", "🧮");
  kv(
    "Size USD",
    `${argv["size-usd"].toFixed(6)} → ${sizeUsdDeltaDisc.toString()} μUSD`,
  );
  if (havePR) {
    kv(
      "Collateral",
      `${argv.collat} → ${collateralTokenDelta.toString()} raw (dec=${decimals})`,
    );
  } else {
    kv("Collateral", `0 (discovery mode; CLI input ${argv.collat})`);
  }
  kv("Guardrail", `${priceGuard.toString()} μUSD`);

  // Step 4 — Build & send — MANUAL TX to enforce instruction order
  bar("Submit", "📤");

  let eventAuthorityPk: PublicKey | null = null;
  try {
    [eventAuthorityPk] = PublicKey.findProgramAddressSync(
      [Buffer.from("__event_authority")],
      programId,
    );
  } catch {}

  const signer = (provider.wallet as any).payer as Keypair;
  let lastValidBlockHeight: number | undefined;
  let reqAtaInit: { ata: PublicKey; ix: any } | null = null;
  let posAtaInit: { ata: PublicKey; ix: any } | null = null;

  if (havePR) {
    const escrowTokenProgramId = await getTokenProgramIdForMint(collateralMint);
    reqAtaInit = createAtaIxStrict(
      wallet.publicKey,
      collateralMint,
      positionRequest,
      /*allowOwnerOffCurve=*/ true,
      escrowTokenProgramId,
    );
    console.log(`🧪 ATA debug (${mintLabel(collateralMint)}, positionRequest):`, {
      mint: shortId(collateralMint.toBase58()),
      owner: shortId(positionRequest.toBase58()),
      allowOwnerOffCurve: true,
      tokenProgramId: shortId(escrowTokenProgramId.toBase58()),
      ata: shortId(reqAtaInit.ata.toBase58()),
    });
    const expectedReqAta = deriveAtaStrict(
      collateralMint,
      positionRequest,
      true,
      escrowTokenProgramId,
    );
    if (!reqAtaInit.ata.equals(expectedReqAta)) {
      throw new Error("ATA mismatch (positionRequest) vs seed derivation");
    }

    posAtaInit = createAtaIxStrict(
      wallet.publicKey,
      collateralMint,
      position,
      /*allowOwnerOffCurve=*/ true,
      escrowTokenProgramId,
    );
    console.log(`🧪 ATA debug (${mintLabel(collateralMint)}, position):`, {
      mint: shortId(collateralMint.toBase58()),
      owner: shortId(position.toBase58()),
      allowOwnerOffCurve: true,
      tokenProgramId: shortId(escrowTokenProgramId.toBase58()),
      ata: shortId(posAtaInit.ata.toBase58()),
    });
    const expectedPosAta = deriveAtaStrict(
      collateralMint,
      position,
      true,
      escrowTokenProgramId,
    );
    if (!posAtaInit.ata.equals(expectedPosAta)) {
      throw new Error("ATA mismatch (position) vs seed derivation");
    }
  }

  const preIxs: any[] = [
    ComputeBudgetProgram.setComputeUnitLimit({ units: argv.cuLimit }),
    ComputeBudgetProgram.setComputeUnitPrice({
      microLamports: argv.priorityMicrolamports,
    }),
  ];

  if (collateralMint.equals(wsolMint)) {
    const ownerPubkey = owner.publicKey;
    const wsolAta = getAssociatedTokenAddressSync(
      wsolMint,
      ownerPubkey,
      /* allowOwnerOffCurve */ false,
      TOKEN_PROGRAM_ID,
      ASSOCIATED_TOKEN_PROGRAM_ID,
    );

    if (ownerPubkey.equals(wsolAta)) {
      throw new Error(
        "BUG: payer equals ATA (would cause 'from must not carry data').",
      );
    }

    const payerInfo = await provider.connection.getAccountInfo(ownerPubkey);
    if (!payerInfo || !payerInfo.owner.equals(SystemProgram.programId)) {
      throw new Error("BUG: payer is not a SystemProgram-owned account.");
    }

    preIxs.push(
      createAssociatedTokenAccountIdempotentInstruction(
        ownerPubkey,
        wsolAta,
        ownerPubkey,
        wsolMint,
        TOKEN_PROGRAM_ID,
        ASSOCIATED_TOKEN_PROGRAM_ID,
      ),
    );
  } else {
    preIxs.push(ownerAtaInit.ix);
  }
  if (reqAtaInit) preIxs.push(reqAtaInit.ix);

  console.log(
    "🧾 preIxs =",
    preIxs.length,
    havePR ? " (owner + req escrow)" : " (owner only)",
  );

  const metas4 = (ix: any) =>
    ix?.keys?.slice(0, 4)?.map((k: any) => k.pubkey.toBase58());
  if (reqAtaInit)
    console.log(
      "AToken escrow[req] metas [payer, ata, owner, mint] =",
      metas4(reqAtaInit.ix),
    );
  if (posAtaInit)
    console.log(
      "AToken escrow[pos] metas [payer, ata, owner, mint] =",
      metas4(posAtaInit.ix),
    );

  if (!eventAuthorityPk) {
    throw new Error("Missing event authority PDA");
  }

  const positionRequestUsdcAta =
    havePR && reqAtaInit ? reqAtaInit.ata : ownerAtaInit.ata;

  const baseArgs = {
    owner: wallet.publicKey,
    perpetualsPk: perpetuals.publicKey,
    poolPk: pool.publicKey,
    positionPk: position,
    positionRequestPk: positionRequest,
    positionRequestUsdcAta,
    ownerUsdcAta: ownerAtaInit.ata,
    marketCustodyPk,
    collateralCustodyPk,
    collateralMintPk: collateralMint,
    referralOrSystemProgram: wallet.publicKey,
    eventAuthorityPk,
    perpsProgramId: programId,
  };

  const previewMode: "idl" | "swapped" = flipCustodyOrder ? "swapped" : "idl";

  const previewAccounts = buildIncreaseAccounts(baseArgs, previewMode);
  console.log(
    "💳 fundingAccount (payer) =",
    previewAccounts.fundingAccount.toBase58(),
    "(collateral ATA)",
  );

  const postIxs: web3.TransactionInstruction[] = [];
  const ixArgs = {
    sizeUsdDelta: sizeUsdDeltaDisc,
    collateralTokenDelta,
    side: sideEnum,
    priceSlippage: priceGuard,
    jupiterMinimumOut: null,
  };

  await rpcPool.runWithFailover(
    async (conn) => {
      await ensureProviderOnConnection(conn);

      const dryRunMode: "idl" | "swapped" = previewMode;
      if (argv["dry-run"]) {
        const accounts = buildIncreaseAccounts(baseArgs, dryRunMode);
        const method = (program as any).methods
          .createIncreasePositionMarketRequest(ixArgs)
          .accountsStrict(accounts)
          .preInstructions(preIxs)
          .postInstructions(postIxs);

        const label =
          dryRunMode === "swapped" ? "dry-run (swapped)" : "dry-run";
        const reqIx = await debugPrintIx(program as Program, method, label);

        const allIxs = [...preIxs, reqIx, ...postIxs];
        const { blockhash, lastValidBlockHeight: lvbh } =
          await provider.connection.getLatestBlockhash();
        lastValidBlockHeight = lvbh;
        const message = new TransactionMessage({
          payerKey: signer.publicKey,
          recentBlockhash: blockhash,
          instructions: allIxs,
        }).compileToV0Message();
        const tx = new VersionedTransaction(message);
        tx.sign([signer]);

        await simulateOrSend(provider.connection, tx, true);
        return true;
      }

      await sendIncreasePositionWithSwapRetry({
        program: program as Program,
        preIxs,
        postIxs,
        ixArgs,
        payer: wallet.publicKey,
        owner: wallet.publicKey,
        perpetualsPk: perpetuals.publicKey,
        poolPk: pool.publicKey,
        positionPk: position,
        positionRequestPk: positionRequest,
        positionRequestUsdcAta,
        ownerUsdcAta: ownerAtaInit.ata,
        marketCustodyPk,
        collateralCustodyPk,
        collateralMintPk: collateralMint,
        referralOrSystemProgram: wallet.publicKey,
        eventAuthorityPk: eventAuthorityPk!,
        perpsProgramId: programId,
      });
      return true;
    },
    "send/createIncreasePositionMarketRequest",
  );

  if (argv["dry-run"]) {
    info("🧪", "Simulation only (dry-run)");
    console.log({ lastValidBlockHeight });
    process.exit(0);
  }

  ok("Tx sent (see signature above)");
  info(
    "📝",
    `PositionRequest = ${positionRequest.toBase58()}  (keeper will execute)\n`,
  );
})();

// --- drop-in replacement for simulateOrSend ---
async function simulateOrSend(
  connection: import("@solana/web3.js").Connection,
  tx: import("@solana/web3.js").VersionedTransaction,
  dryRun: boolean,
) {
  if (dryRun) {
    console.log("🧪 dry-run: simulating transaction (no send)");
    const sim = await connection.simulateTransaction(tx, {
      sigVerify: false,
      replaceRecentBlockhash: true,
    });
    if (sim.value.err) console.error("❌ simulate err:", sim.value.err);
    if (sim.value.logs?.length) {
      console.log("🧾 simulate logs (compact):");
      for (const l of formatLogs(sim.value.logs)) console.log("   ", l);
    }
    if (!sim.value.err) {
      console.log("✅ simulation success");
    }
    return;
  }

  try {
    const sig = await connection.sendTransaction(tx, {
      skipPreflight: false,
      maxRetries: 3,
    });
    console.log("✅ sent:", sig);
  } catch (err: any) {
    console.error("❌ sendTransaction error:", err);
    if (typeof err.getLogs === "function") {
      const logs = await err.getLogs().catch(() => null);
      if (logs?.length) {
        console.error("🧾 send logs (compact):");
        for (const l of formatLogs(logs)) console.error("   ", l);
      }
    } else if (err?.transactionLogs?.length) {
      console.error("🧾 send logs (compact):");
      for (const l of formatLogs(err.transactionLogs)) console.error("   ", l);
    }
    throw err;
  }
}

