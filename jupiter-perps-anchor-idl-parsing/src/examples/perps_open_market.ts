/* Open/Increase position at market, with optional collateral deposit */
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import type { Idl } from "@coral-xyz/anchor";
import { PublicKey, SystemProgram, Keypair, Transaction } from "@solana/web3.js";
import { bar, info, kv, ok, fail } from "../utils/logger.js";
import * as cfg from "../config/perps.js";
import { toMicroUsd, toTokenAmount, derivePdaFromIdl, sideToEnum } from "../utils/resolve.js";
import { IDL as JUP_PERPS_IDL } from "../idl/jupiter-perpetuals-idl.js";

(async () => {
  const argv = await yargs(hideBin(process.argv))
    .option("rpc", { type: "string", demandOption: true })
    .option("kp", { type: "string", demandOption: true, describe: "Path to keypair JSON/base58" })
    .option("market", { type: "string", choices: ["SOL", "ETH", "BTC"] as const, demandOption: true })
    .option("side", { type: "string", choices: ["long", "short"] as const, demandOption: true })
    .option("size-usd", { type: "number", demandOption: true, describe: "USD notional for size" })
    .option("collat", { type: "number", default: 0, describe: "Collateral token amount (UI units)" })
    .option("collat-mint", { type: "string", describe: "Override collateral mint (default: WSOL for long, USDC for short)" })
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
  const collateralMint = new PublicKey(argv["collat-mint"] ?? defaultCollat);
  const collateralCustody = await cfg.findCustodyByMint(program, pool.account, collateralMint);

  bar("PDAs", "🧩");
  const [position] = derivePdaFromIdl(JUP_PERPS_IDL as Idl, programId, "position", {
    owner: wallet.publicKey,
    pool: pool.publicKey,
    custody: custody.pubkey,
    collateralCustody: collateralCustody.pubkey,
  });
  const unique = Math.floor(Date.now() / 1000);
  const [positionRequest] = derivePdaFromIdl(JUP_PERPS_IDL as Idl, programId, "positionRequest", {
    owner: wallet.publicKey,
    pool: pool.publicKey,
    custody: custody.pubkey,
    collateralCustody: collateralCustody.pubkey,
    seed: unique,
    position,
  });
  kv("Position", position.toBase58());
  kv("PosRequest", positionRequest.toBase58());

  // 2) Funding (owner ATA) & PositionRequest ATA (escrow)
  const ataInit = await cfg.ensureAtaIx(provider.connection, collateralMint, wallet.publicKey, wallet.publicKey);
  const prAtaInit = await cfg.ensureAtaForOwner(provider.connection, collateralMint, positionRequest, wallet.publicKey, true);

  const decimals = (collateralCustody.account.decimals as number) ?? 9;
  const collateralTokenDelta = toTokenAmount(argv.collat, decimals);
  const needsCollateral = (collateralTokenDelta.gt ? collateralTokenDelta.gt(new cfg.BN(0)) : collateralTokenDelta > 0);
  const topUp = collateralMint.equals(cfg.MINTS.WSOL)
    ? await cfg.topUpWsolIfNeededIx(provider.connection, ataInit.ata, wallet.publicKey, BigInt(collateralTokenDelta.toString()))
    : [];
  const preIxs = needsCollateral ? [...ataInit.ixs, ...prAtaInit.ixs, ...topUp] : [];

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
    fundingAccount: ataInit.ata,
    position,
    positionRequest,
    positionRequestAta: prAtaInit.ata,
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

  try {
    const [eventAuthority] = PublicKey.findProgramAddressSync([Buffer.from("__event_authority")], programId);
    (accounts as any).eventAuthority = eventAuthority;
    (accounts as any).program = programId;
  } catch {}

  // Build the Perps request instruction
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

  // Force order: create ATAs / wrap WSOL first, then Perps ix
  const tx = new Transaction();
  if (preIxs.length) tx.add(...preIxs);
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
