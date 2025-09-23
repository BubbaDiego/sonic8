/* Open/Increase position at market, with optional collateral deposit */
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import type { Idl } from "@coral-xyz/anchor";
import { PublicKey, SystemProgram, Keypair, Transaction } from "@solana/web3.js";
import { NATIVE_MINT } from "@solana/spl-token";
import { bar, info, kv, ok, fail } from "../utils/logger.js";
import * as cfg from "../config/perps.js";
import { toMicroUsd, toTokenAmount, derivePdaFromIdl, derivePositionPdaCanonical, derivePositionPdaPoolFirst, derivePositionPdaOwnerFirst, sideToEnum } from "../utils/resolve.js";
import { IDL as JUP_PERPS_IDL } from "../idl/jupiter-perpetuals-idl.js";
import { toPk } from "../utils/pk.js";

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
    .option("position-request", { type: "string", describe: "Override PositionRequest PDA (use Perps Right: value)" })
    .option("oracle-price", { type: "number", describe: "Oracle/mark price in USD for guardrail calc" })
    .option("slip", { type: "number", describe: "Slippage fraction for guardrail (e.g., 0.02)" })
    .option("max-price", { type: "number", describe: "Explicit max price (LONG)" })
    .option("min-price", { type: "number", describe: "Explicit min price (SHORT)" })
    .option("dry-run", { type: "boolean", default: false })
    .strict()
    .parse();

  const { program, programId, provider, wallet } = cfg.bootstrap(argv.rpc, argv.kp);

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
  const positionRequestOverride = argv["position-request"]
    ? toPk("position-request", argv["position-request"] as string)
    : null;

  const [derivedPositionRequest] = derivePdaFromIdl(JUP_PERPS_IDL as Idl, programId, "positionRequest", {
    owner: wallet.publicKey,
    pool: pool.publicKey,
    custody: custody.pubkey,
    collateralCustody: collateralCustody.pubkey,
    seed: unique,
    position,
  });
  const positionRequest = positionRequestOverride ?? derivedPositionRequest;
  kv("Position", position.toBase58());
  kv("PosRequest", positionRequest.toBase58());
  if (positionRequestOverride) {
    console.log("🧩 positionRequest (override) =", positionRequestOverride.toBase58());
  }

  const decimals = (collateralCustody.account.decimals as number) ?? 9;
  const collateralTokenDelta = toTokenAmount(argv.collat, decimals);

  // 2) Funding (owner ATA) & escrow ATAs (position request + position)
  // 1) Owner's USDC ATA (funding) – usually already exists
  const ownerAtaInit = await cfg.ensureAtaIx(
    provider.connection,
    collateralMint,
    wallet.publicKey,
    wallet.publicKey,
  );

  // 2) Escrow A: owner = positionRequest PDA
  const reqAtaInit = await cfg.ensureAtaForOwner(
    provider.connection,
    collateralMint,
    positionRequest,
    wallet.publicKey,
    true,
  );

  // 3) Escrow B: owner = position PDA (Perps may idempotently ensure this too)
  const posAtaInit = await cfg.ensureAtaForOwner(
    provider.connection,
    collateralMint,
    position,
    wallet.publicKey,
    true,
  );

  // Compose pre-ixs: owner first (if missing), then both escrows
  const preIxs = [...ownerAtaInit.ixs, ...reqAtaInit.ixs, ...posAtaInit.ixs];

  console.log(
    "🧾 preIxs =",
    preIxs.length,
    " (owner create:",
    ownerAtaInit.ixs.length,
    ", req escrow create:",
    reqAtaInit.ixs.length,
    ", pos escrow create:",
    posAtaInit.ixs.length,
    ")",
  );

  // For transparency (first 4 metas):
  const meta4 = (ix: any) => ix?.keys?.slice(0, 4)?.map((k: any) => k.pubkey.toBase58());
  if (reqAtaInit.ixs[0]) console.log("AToken escrow[req] metas [payer, ata, owner, mint] =", meta4(reqAtaInit.ixs[0]));
  if (posAtaInit.ixs[0]) console.log("AToken escrow[pos] metas [payer, ata, owner, mint] =", meta4(posAtaInit.ixs[0]));

  // 3) Amounts & guardrail
  const sizeUsdDelta = toMicroUsd(argv["size-usd"]);
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
  kv("Size USD", `${argv["size-usd"].toFixed(6)} → ${sizeUsdDelta.toString()} μUSD`);
  kv("Collateral", `${argv.collat} → ${collateralTokenDelta.toString()} raw (dec=${decimals})`);
  kv("Guardrail", `${priceGuard.toString()} μUSD`);

  // 4) Build & send — MANUAL TX to enforce instruction order
  bar("Submit", "📤");

  const accounts: Record<string, PublicKey> = {
    owner: wallet.publicKey,
    fundingAccount: ownerAtaInit.ata,         // ✅ Token account (Token Program–owned)
    position,
    positionRequest,
    positionRequestAta: reqAtaInit.ata,       // ✅ Escrow bound to PositionRequest
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

  console.log("💳 fundingAccount (ATA) =", (accounts as any).fundingAccount.toBase58());

  try {
    const [eventAuthority] = PublicKey.findProgramAddressSync([Buffer.from("__event_authority")], programId);
    (accounts as any).eventAuthority = eventAuthority;
    (accounts as any).program = programId;
  } catch {}

  const reqIx = await (program as any).methods
    .createIncreasePositionMarketRequest({
      sizeUsdDelta,
      collateralTokenDelta,
      side: sideEnum,
      priceSlippage: priceGuard,
      jupiterMinimumOut: null,
    })
    .accounts(accounts)
    .instruction();

  const tx = new Transaction();
  if (preIxs.length) tx.add(...preIxs);   // ✅ AToken creates first
  tx.add(reqIx);
  tx.feePayer = wallet.publicKey;
  tx.recentBlockhash = (await provider.connection.getLatestBlockhash()).blockhash;

  if (argv["dry-run"]) {
    info("🧪", "Simulation only (dry-run)");
    const sim = await provider.connection.simulateTransaction(tx, [(provider.wallet as any).payer as Keypair]);
    console.log(sim);
    process.exit(0);
  }

  const sig = await provider.sendAndConfirm(tx, [(provider.wallet as any).payer as Keypair]);
  ok(`Tx sent: ${sig}`);
  info("📝", `PositionRequest = ${positionRequest.toBase58()}  (keeper will execute)\n`);
})();
