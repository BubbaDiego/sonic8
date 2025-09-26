/* Open/Increase position at market, with optional collateral deposit */
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import type { Idl } from "@coral-xyz/anchor";
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
import { bar, info, kv, ok, fail } from "../utils/logger.js";
import * as cfg from "../config/perps.js";
import { toMicroUsd, toTokenAmount, derivePdaFromIdl, derivePositionPdaCanonical, derivePositionPdaPoolFirst, derivePositionPdaOwnerFirst, sideToEnum } from "../utils/resolve.js";
import { IDL as JUP_PERPS_IDL } from "../idl/jupiter-perpetuals-idl.js";
import { toPk } from "../utils/pk.js";
import { createAtaIxStrict, deriveAtaStrict, detectTokenProgramForMint } from "../utils/ata.js";

(async () => {
  const argv = await yargs(hideBin(process.argv))
    .option("rpc", { type: "string", demandOption: true })
    .option("kp", { type: "string", demandOption: true, describe: "Path to keypair JSON/base58" })
    .option("market", { type: "string", choices: ["SOL", "ETH", "BTC"] as const, demandOption: true })
    .option("side", { type: "string", choices: ["long", "short"] as const, demandOption: true })
    .option("size-usd", { type: "number", demandOption: true, describe: "USD notional for size" })
    .option("collat", { type: "number", default: 0, describe: "Collateral token amount (UI units)" })
    .option("collat-mint", { type: "string", describe: "Override collateral mint (default: WSOL for long, USDC for short)" })
    .option("position", { type: "string", describe: "Override Position PDA (use the Right: value from logs)" })
    .option("position-request", { type: "string", describe: "Override PositionRequest PDA (use Perps 'Right:' value)" })
    .option("oracle-price", { type: "number", describe: "Oracle/mark price in USD for guardrail calc" })
    .option("slip", { type: "number", describe: "Slippage fraction for guardrail (e.g., 0.02)" })
    .option("max-price", { type: "number", describe: "Explicit max price (LONG)" })
    .option("min-price", { type: "number", describe: "Explicit min price (SHORT)" })
    .option("dry-run", { type: "boolean", default: false })
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

  const { program, programId, provider, wallet } = cfg.bootstrap(argv.rpc, argv.kp);
  const connection = provider.connection;
  const owner = (provider.wallet as any).payer as Keypair;

  // 1) Discover accounts
  const perpetuals = await cfg.getSingletonPerpetuals(program);
  const pool = await cfg.getSingletonPool(program);

  const marketMint = (cfg.MINTS as any)[argv.market] as PublicKey;
  const sideEnum = sideToEnum(argv.side);

  const custody = await cfg.findCustodyByMint(program, pool.account, marketMint);
  const defaultCollat = argv.side === "long" ? marketMint : cfg.MINTS.USDC;
  const collatMintArg = (argv["collat-mint"] as unknown) ?? null;
  const collateralMint = collatMintArg ? toPk("collat-mint", collatMintArg) : defaultCollat;
  console.log(
    "🔑  Mints :: marketMint=",
    (marketMint as any).toBase58?.() ?? String(marketMint),
    " collateralMint=",
    (collateralMint as any).toBase58?.() ?? String(collateralMint),
  );
  const collateralCustody = await cfg.findCustodyByMint(program, pool.account, collateralMint);

  bar("PDAs", "🧩");
  const [positionCanonical] = derivePositionPdaCanonical(
    programId,
    pool.publicKey,
    custody.pubkey,
    wallet.publicKey,
  );
  let position: PublicKey;
  if (argv.position) {
    position = toPk("position", argv.position);
    console.log("🧩 position (override) =", position.toBase58());
  } else {
    position = positionCanonical;
    console.log("🧩 position =", position.toBase58());
  }
  const [posPoolFirst]  = derivePositionPdaPoolFirst(programId, pool.publicKey, wallet.publicKey);
  const [posOwnerFirst] = derivePositionPdaOwnerFirst(programId, wallet.publicKey, pool.publicKey);

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
    const [derivedPositionRequest] = derivePdaFromIdl(JUP_PERPS_IDL as Idl, programId, "positionRequest", {
      owner: wallet.publicKey,
      pool: pool.publicKey,
      custody: custody.pubkey,
      collateralCustody: collateralCustody.pubkey,
      seed: unique,
      position,
    });
    positionRequest = derivedPositionRequest;
  }
  kv("Position", position.toBase58());
  kv("PosRequest", positionRequest.toBase58());

  const decimals = (collateralCustody.account.decimals as number) ?? 9;
  // Discovery run = no token transfer → set collat=0 on the wire when !havePR
  const sizeUsdDeltaDisc = toMicroUsd(argv["size-usd"]);
  const collateralTokenDelta = havePR
    ? toTokenAmount(argv.collat, decimals)
    : new cfg.BN(0);                          // discovery → 0 on-chain

  // 2) Funding (owner ATA) & escrow ATAs (position request + position)
  const usdcMint = new PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v");
  const wsolMint = new PublicKey("So11111111111111111111111111111111111111112");

  const usdcProgramId = await detectTokenProgramForMint(provider.connection, usdcMint);
  const wsolProgramId = await detectTokenProgramForMint(provider.connection, wsolMint);

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
    mint: collateralMint.toBase58(),
    owner: wallet.publicKey.toBase58(),
    allowOwnerOffCurve: false,
    tokenProgramId: ownerTokenProgramId.toBase58(),
    ata: ownerAtaInit.ata.toBase58(),
  });
  const expectedOwnerAta = deriveAtaStrict(collateralMint, wallet.publicKey, false, ownerTokenProgramId);
  if (!ownerAtaInit.ata.equals(expectedOwnerAta)) {
    throw new Error("ATA mismatch (wallet) vs seed derivation");
  }

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
      mint: collateralMint.toBase58(),
      owner: positionRequest.toBase58(),
      allowOwnerOffCurve: true,
      tokenProgramId: escrowTokenProgramId.toBase58(),
      ata: reqAtaInit.ata.toBase58(),
    });
    const expectedReqAta = deriveAtaStrict(collateralMint, positionRequest, true, escrowTokenProgramId);
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
      mint: collateralMint.toBase58(),
      owner: position.toBase58(),
      allowOwnerOffCurve: true,
      tokenProgramId: escrowTokenProgramId.toBase58(),
      ata: posAtaInit.ata.toBase58(),
    });
    const expectedPosAta = deriveAtaStrict(collateralMint, position, true, escrowTokenProgramId);
    if (!posAtaInit.ata.equals(expectedPosAta)) {
      throw new Error("ATA mismatch (position) vs seed derivation");
    }
  }

  const preIxs: any[] = [];
  preIxs.unshift(
    ComputeBudgetProgram.setComputeUnitLimit({ units: argv.cuLimit }),
    ComputeBudgetProgram.setComputeUnitPrice({ microLamports: argv.priorityMicrolamports }),
  );
  if (collateralMint.equals(wsolMint)) {
    // --- WSOL ATA for the wallet owner ---
    // owner should be your Keypair loaded from --kp
    const ownerPubkey = owner.publicKey;
    const wsolMint = new PublicKey("So11111111111111111111111111111111111111112");

    // Derive ATA deterministically (no off-curve owner)
    const wsolAta = getAssociatedTokenAddressSync(
      wsolMint,
      ownerPubkey,
      /* allowOwnerOffCurve */ false,
      TOKEN_PROGRAM_ID,
      ASSOCIATED_TOKEN_PROGRAM_ID
    );

    // Safety guard: payer must be a system account and must NOT equal the ATA
    if (ownerPubkey.equals(wsolAta)) {
      throw new Error("BUG: payer equals ATA (would cause 'from must not carry data').");
    }

    // Optional runtime sanity: ensure payer is system-owned
    const payerInfo = await connection.getAccountInfo(ownerPubkey);
    if (!payerInfo || !payerInfo.owner.equals(SystemProgram.programId)) {
      throw new Error("BUG: payer is not a SystemProgram-owned account.");
    }

    // Create the ATA idempotently with the *owner system account* as payer
    preIxs.push(
      createAssociatedTokenAccountIdempotentInstruction(
        ownerPubkey,          // payer (system account with no data)
        wsolAta,              // ata to create (if missing)
        ownerPubkey,          // token owner
        wsolMint,             // mint
        TOKEN_PROGRAM_ID,
        ASSOCIATED_TOKEN_PROGRAM_ID
      )
    );

    // (Keep your logs if you like)
    console.log("🧾 preIxs = %d  (owner only)", preIxs.length);
  } else {
    preIxs.push(ownerAtaInit.ix);
  }
  if (reqAtaInit) preIxs.push(reqAtaInit.ix);
  if (posAtaInit) preIxs.push(posAtaInit.ix);
  console.log(
    "🧾 preIxs =",
    preIxs.length,
    havePR ? " (owner + req escrow + pos escrow)" : " (owner only)",
  );

  // For transparency (first 4 metas):
  const metas4 = (ix: any) => ix?.keys?.slice(0, 4)?.map((k: any) => k.pubkey.toBase58());
  if (reqAtaInit) console.log("AToken escrow[req] metas [payer, ata, owner, mint] =", metas4(reqAtaInit.ix));
  if (posAtaInit) console.log("AToken escrow[pos] metas [payer, ata, owner, mint] =", metas4(posAtaInit.ix));

  // 3) Amounts & guardrail
  let priceGuard: cfg.BN | null = null;
  if (typeof argv["oracle-price"] === "number" && typeof argv["slip"] === "number") {
    const factor = argv.side === "long" ? (1 + argv.slip) : (1 - argv.slip);
    priceGuard = toMicroUsd(argv["oracle-price"] * factor);
  } else if (typeof argv["max-price"] === "number" && argv.side === "long") {
    priceGuard = toMicroUsd(argv["max-price"]);
  } else if (typeof argv["min-price"] === "number" && argv.side === "short") {
    priceGuard = toMicroUsd(argv["min-price"]);
  }
  if (!priceGuard) {
    fail("No price guardrail provided. Use --oracle-price + --slip or --max-price/--min-price.");
    process.exit(1);
  }

  bar("Amounts", "🧮");
  kv("Size USD", `${argv["size-usd"].toFixed(6)} → ${sizeUsdDeltaDisc.toString()} μUSD`);
  if (havePR) {
    kv("Collateral", `${argv.collat} → ${collateralTokenDelta.toString()} raw (dec=${decimals})`);
  } else {
    kv("Collateral", `0 (discovery mode; CLI input ${argv.collat})`);
  }
  kv("Guardrail", `${priceGuard.toString()} μUSD`);

  // 4) Build & send — MANUAL TX to enforce instruction order
  bar("Submit", "📤");

  const accounts: Record<string, PublicKey> = {
    owner: wallet.publicKey,
    // ✅ always use the collateral ATA for funding
    fundingAccount: ownerAtaInit.ata,
    position,
    positionRequest,
    positionRequestAta: havePR ? reqAtaInit.ata : ownerAtaInit.ata,
    custody: custody.pubkey,
    collateralCustody: collateralCustody.pubkey,
    inputMint: collateralMint,
    referral: wallet.publicKey,
    perpetuals: perpetuals.publicKey,
    pool: pool.publicKey,
    tokenProgram: cfg.SYS.TOKEN_PROGRAM_ID,
    associatedTokenProgram: cfg.SYS.ASSOCIATED_TOKEN_PROGRAM_ID,
    systemProgram: SystemProgram.programId,
  } as any;

  console.log(
    "💳 fundingAccount (payer) =",
    (accounts as any).fundingAccount.toBase58(),
    "(collateral ATA)",
  );

  try {
    const [eventAuthority] = PublicKey.findProgramAddressSync([Buffer.from("__event_authority")], programId);
    (accounts as any).eventAuthority = eventAuthority;
    (accounts as any).program = programId;
  } catch {}

  const reqIx = await (program as any).methods
    .createIncreasePositionMarketRequest({
      sizeUsdDelta: sizeUsdDeltaDisc,
      collateralTokenDelta,
      side: sideEnum,
      priceSlippage: priceGuard,
      jupiterMinimumOut: null,
    })
    .accounts(accounts)
    .instruction();

  const signer = (provider.wallet as any).payer as Keypair;
  const allIxs = preIxs.length ? [...preIxs, reqIx] : [reqIx];
  const { blockhash, lastValidBlockHeight } = await provider.connection.getLatestBlockhash();
  const message = new TransactionMessage({
    payerKey: signer.publicKey,
    recentBlockhash: blockhash,
    instructions: allIxs,
  }).compileToV0Message();
  const tx = new VersionedTransaction(message);
  tx.sign([signer]);

  await simulateOrSend(provider.connection, tx, argv["dry-run"] === true);

  if (argv["dry-run"]) {
    info("🧪", "Simulation only (dry-run)");
    console.log({ lastValidBlockHeight });
    process.exit(0);
  }

  ok("Tx sent (see signature above)");
  info("📝", `PositionRequest = ${positionRequest.toBase58()}  (keeper will execute)\n`);
})();

// --- drop-in replacement for simulateOrSend ---
async function simulateOrSend(
  connection: import("@solana/web3.js").Connection,
  tx: import("@solana/web3.js").VersionedTransaction,
  dryRun: boolean
) {
  if (dryRun) {
    // Correct modern signature: options object, not a signers array.
    const sim = await connection.simulateTransaction(tx, {
      sigVerify: false,
      replaceRecentBlockhash: true
    });
    if (sim.value.err) {
      console.error("❌ simulate err:", sim.value.err);
    }
    if (sim.value.logs?.length) {
      console.log("🧾 simulate logs:");
      for (const l of sim.value.logs) console.log("   ", l);
    }
    console.log("🧪 dry-run complete (no tx sent).");
    return;
  }

  // Live path (unchanged, but shown for clarity)
  const sig = await connection.sendTransaction(tx, {
    skipPreflight: false,
    maxRetries: 3
  });
  console.log("✅ sent:", sig);
}
