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

type CustodyInfo = { pubkey: PublicKey; account: any; mint: PublicKey };

function pickCustodyByMint(custodies: CustodyInfo[], mint: PublicKey) {
  const c = custodies.find((x) => x.mint.equals(mint));
  if (!c) throw new Error(`No custody found for mint ${mint.toBase58()}`);
  return c;
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
      if (pid) out.push(`• ${labelFor(pid)} → ${l.replace(/^Program\s+[A-Za-z0-9]+\s/, "")}`);
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

  const allCustodiesRaw = await cfg.getCustodies(program, pool.account);
  const allCustodies: CustodyInfo[] = allCustodiesRaw.map((c) => ({
    ...c,
    mint: new PublicKey(c.account.mint as PublicKey),
  }));

  const marketCustody = pickCustodyByMint(allCustodies, marketMint);
  const defaultCollat = argv.side === "long" ? marketMint : cfg.MINTS.USDC;
  const collatMintArg = (argv["collat-mint"] as unknown) ?? null;
  const collateralMint = collatMintArg ? toPk("collat-mint", collatMintArg) : defaultCollat;
  let collateralCustody = pickCustodyByMint(allCustodies, collateralMint);
  console.log(
    "🔑  Mints :: marketMint=",
    (marketMint as any).toBase58?.() ?? String(marketMint),
    " collateralMint=",
    (collateralMint as any).toBase58?.() ?? String(collateralMint),
  );
  console.log("🧪 custody (market):     ", marketCustody.pubkey.toBase58());
  console.log("🧪 collateral_custody:  ", collateralCustody.pubkey.toBase58());
  console.log("🧪 input_mint:          ", collateralMint.toBase58());

  bar("PDAs", "🧩");
  const [positionCanonical] = derivePositionPdaCanonical(
    programId,
    pool.publicKey,
    marketCustody.pubkey,
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
      custody: marketCustody.pubkey,
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
    mint: shortId(collateralMint.toBase58()),
    owner: shortId(wallet.publicKey.toBase58()),
    allowOwnerOffCurve: false,
    tokenProgramId: shortId(ownerTokenProgramId.toBase58()),
    ata: shortId(ownerAtaInit.ata.toBase58()),
  });
  const expectedOwnerAta = deriveAtaStrict(collateralMint, wallet.publicKey, false, ownerTokenProgramId);
  if (!ownerAtaInit.ata.equals(expectedOwnerAta)) {
    throw new Error("ATA mismatch (wallet) vs seed derivation");
  }

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

  let eventAuthority: PublicKey | null = null;
  try {
    [eventAuthority] = PublicKey.findProgramAddressSync([Buffer.from("__event_authority")], programId);
  } catch {}

  const signer = (provider.wallet as any).payer as Keypair;
  let lastValidBlockHeight: number | undefined;
  let pendingCollateralOverride: CustodyInfo | null = null;
  let didAutoAlignCollateral = false;
  let activePositionRequest = positionRequest;
  let activeCollateralCustody = collateralCustody;
  let sendErr: any = null;

  for (let attempt = 1; attempt <= 2; attempt++) {
    if (pendingCollateralOverride) {
      activeCollateralCustody = pendingCollateralOverride;
      pendingCollateralOverride = null;
      if (!havePR) {
        const [derivedPositionRequest] = derivePdaFromIdl(JUP_PERPS_IDL as Idl, programId, "positionRequest", {
          owner: wallet.publicKey,
          pool: pool.publicKey,
          custody: marketCustody.pubkey,
          collateralCustody: activeCollateralCustody.pubkey,
          seed: unique,
          position,
        });
        activePositionRequest = derivedPositionRequest;
        console.log("🔧 auto-align: position_request →", activePositionRequest.toBase58());
      }
    }

    let reqAtaInit: { ata: PublicKey; ix: any } | null = null;
    let posAtaInit: { ata: PublicKey; ix: any } | null = null;

    if (havePR) {
      const escrowTokenProgramId = await getTokenProgramIdForMint(collateralMint);
      reqAtaInit = createAtaIxStrict(
        wallet.publicKey,
        collateralMint,
        activePositionRequest,
        /*allowOwnerOffCurve=*/ true,
        escrowTokenProgramId,
      );
      console.log(`🧪 ATA debug (${mintLabel(collateralMint)}, positionRequest):`, {
        mint: shortId(collateralMint.toBase58()),
        owner: shortId(activePositionRequest.toBase58()),
        allowOwnerOffCurve: true,
        tokenProgramId: shortId(escrowTokenProgramId.toBase58()),
        ata: shortId(reqAtaInit.ata.toBase58()),
      });
      const expectedReqAta = deriveAtaStrict(collateralMint, activePositionRequest, true, escrowTokenProgramId);
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
      const expectedPosAta = deriveAtaStrict(collateralMint, position, true, escrowTokenProgramId);
      if (!posAtaInit.ata.equals(expectedPosAta)) {
        throw new Error("ATA mismatch (position) vs seed derivation");
      }
    }

    const preIxs: any[] = [
      ComputeBudgetProgram.setComputeUnitLimit({ units: argv.cuLimit }),
      ComputeBudgetProgram.setComputeUnitPrice({ microLamports: argv.priorityMicrolamports }),
    ];

    if (collateralMint.equals(wsolMint)) {
      const ownerPubkey = owner.publicKey;
      const wsolAta = getAssociatedTokenAddressSync(
        wsolMint,
        ownerPubkey,
        /* allowOwnerOffCurve */ false,
        TOKEN_PROGRAM_ID,
        ASSOCIATED_TOKEN_PROGRAM_ID
      );

      if (ownerPubkey.equals(wsolAta)) {
        throw new Error("BUG: payer equals ATA (would cause 'from must not carry data').");
      }

      const payerInfo = await connection.getAccountInfo(ownerPubkey);
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
          ASSOCIATED_TOKEN_PROGRAM_ID
        )
      );
    } else {
      preIxs.push(ownerAtaInit.ix);
    }
    if (reqAtaInit) preIxs.push(reqAtaInit.ix);
    if (posAtaInit) preIxs.push(posAtaInit.ix);

    console.log(
      "🧾 preIxs =",
      preIxs.length,
      havePR ? " (owner + req escrow + pos escrow)" : " (owner only)",
      attempt > 1 ? " [retry]" : "",
    );

    const metas4 = (ix: any) => ix?.keys?.slice(0, 4)?.map((k: any) => k.pubkey.toBase58());
    if (reqAtaInit) console.log("AToken escrow[req] metas [payer, ata, owner, mint] =", metas4(reqAtaInit.ix));
    if (posAtaInit) console.log("AToken escrow[pos] metas [payer, ata, owner, mint] =", metas4(posAtaInit.ix));

    const accounts: { [key: string]: PublicKey } = {
      owner: wallet.publicKey,
      funding_account: ownerAtaInit.ata,
      perpetuals: perpetuals.publicKey,
      pool: pool.publicKey,
      position,
      position_request: activePositionRequest,
      position_request_ata: havePR && reqAtaInit ? reqAtaInit.ata : ownerAtaInit.ata,
      custody: marketCustody.pubkey,
      collateral_custody: activeCollateralCustody.pubkey,
      input_mint: collateralMint,
      referral: wallet.publicKey,
      token_program: cfg.SYS.TOKEN_PROGRAM_ID,
      associated_token_program: cfg.SYS.ASSOCIATED_TOKEN_PROGRAM_ID,
      system_program: SystemProgram.programId,
    };

    console.log(
      "💳 funding_account (payer) =",
      accounts["funding_account"].toBase58(),
      "(collateral ATA)",
    );

    if (eventAuthority) {
      accounts["event_authority"] = eventAuthority;
      accounts["program"] = programId;
    }

    const custodyPk = accounts["custody"];
    const collateralPk = accounts["collateral_custody"];
    if (!custodyPk.equals(marketCustody.pubkey)) {
      throw new Error("custody mismatch: not market custody");
    }
    if (!collateralPk.equals(activeCollateralCustody.pubkey)) {
      throw new Error("collateral_custody mismatch: not USDC custody");
    }

    const reqIx = await (program as any).methods
      .createIncreasePositionMarketRequest({
        sizeUsdDelta: sizeUsdDeltaDisc,
        collateralTokenDelta,
        side: sideEnum,
        priceSlippage: priceGuard,
        jupiterMinimumOut: null,
      })
      .accountsStrict(accounts)
      .instruction();

    const allIxs = preIxs.length ? [...preIxs, reqIx] : [reqIx];
    const { blockhash, lastValidBlockHeight: lvbh } = await provider.connection.getLatestBlockhash();
    lastValidBlockHeight = lvbh;
    const message = new TransactionMessage({
      payerKey: signer.publicKey,
      recentBlockhash: blockhash,
      instructions: allIxs,
    }).compileToV0Message();
    const tx = new VersionedTransaction(message);
    tx.sign([signer]);

    try {
      await simulateOrSend(provider.connection, tx, argv["dry-run"] === true);
      positionRequest = activePositionRequest;
      collateralCustody = activeCollateralCustody;
      sendErr = null;
      break;
    } catch (err: any) {
      sendErr = err;
      if (argv["dry-run"]) throw err;
      const rawLogs = await extractTransactionLogs(err);
      const nextCollateralPk = rawLogs ? tryAutoAlignCollateralFromLogs(rawLogs, allCustodies) : null;
      if (!nextCollateralPk || didAutoAlignCollateral) throw err;
      const nextCollateral = allCustodies.find((c) => c.pubkey.equals(nextCollateralPk));
      if (!nextCollateral) throw err;
      if (nextCollateral.pubkey.equals(activeCollateralCustody.pubkey)) throw err;
      didAutoAlignCollateral = true;
      console.log("\n🔧 auto-align: collateral_custody →", nextCollateral.pubkey.toBase58());
      pendingCollateralOverride = nextCollateral;
      continue;
    }
  }

  if (sendErr) throw sendErr;

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

async function extractTransactionLogs(err: any): Promise<string[] | null> {
  if (!err) return null;
  if (Array.isArray(err.transactionLogs)) return err.transactionLogs;
  if (Array.isArray(err.logs)) return err.logs;
  if (typeof err.getLogs === "function") {
    try {
      const logs = await err.getLogs();
      if (Array.isArray(logs)) return logs;
      if (Array.isArray((logs as any)?.logs)) return (logs as any).logs;
    } catch {}
  }
  return null;
}

function parseInvalidCollateralFromLogs(logs: string[]): { left: string; right: string } | null {
  const base58 = /[1-9A-HJ-NP-Za-km-z]{32,44}/;
  const i = logs.findIndex((l) => l.includes("Invalid collateral account"));
  if (i < 0) return null;

  const window = logs.slice(i, i + 10);
  const leftLine = window.find((l) => l.includes("Left"));
  const rightLine = window.find((l) => l.includes("Right"));
  if (!leftLine || !rightLine) return null;

  const leftMatch = leftLine.match(base58);
  const rightMatch = rightLine.match(base58);
  if (!leftMatch || !rightMatch) return null;

  const left = leftMatch[0];
  const right = rightMatch[0];
  return { left, right };
}

function tryAutoAlignCollateralFromLogs(logs: string[], allCustodies: CustodyInfo[]): PublicKey | null {
  const parsed = parseInvalidCollateralFromLogs(logs);
  if (!parsed) return null;
  const { left, right } = parsed;

  console.warn("⚠️ InvalidCollateralAccount: provided =", left, " expected =", right);

  const expected = allCustodies.find((c) => c.pubkey.toBase58() === right);
  return expected ? expected.pubkey : null;
}
