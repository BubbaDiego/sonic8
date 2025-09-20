// Minimal CLI that returns the exact accounts + remaining accounts
// for createIncreasePositionMarketRequest.

import { Connection, PublicKey } from "@solana/web3.js";
import { getAssociatedTokenAddressSync } from "@solana/spl-token";

import { MARKETS, PERPETUALS_PROGRAM_ID, USDC_MINT } from "./perps_constants.js";
import { generatePositionAndPositionRequestPda } from "./generate-position-and-position-request-pda.js";
import { remainingAccountsForCreateIncreasePositionMarketRequest } from "./remaining-accounts.js";
import type { Side } from "./types.js";

type Args = {
  market: string;
  side: "long" | "short";
  sizeUsd: number;
  collateralUsd: number;
  owner: string;
  rpc?: string;
};

function parseArgs(): Args {
  const a = new Map<string, string>();
  for (let i = 2; i < process.argv.length; i += 2) {
    const k = process.argv[i]?.replace(/^--/, "");
    const v = process.argv[i + 1];
    if (k) a.set(k, v ?? "");
  }
  const market = a.get("market") ?? "";
  const side = (a.get("side") ?? "").toLowerCase() as Args["side"];
  const sizeUsd = Number(a.get("size-usd") ?? a.get("sizeUsd") ?? "0");
  const collateralUsd = Number(
    a.get("collateral-usd") ?? a.get("collateralUsd") ?? "0"
  );
  const owner = a.get("owner") ?? "";
  const envKey = process.env.HELIUS_API_KEY ? `https://rpc.helius.xyz/?api-key=${process.env.HELIUS_API_KEY}` : undefined;
  const rpc = a.get("rpc") ?? process.env.HELIUS_RPC_URL ?? envKey;

  if (!market || !owner || (side !== "long" && side !== "short")) {
    console.error(
      JSON.stringify(
        {
          ok: false,
          error: "missing-args",
          hint:
            "required: --market, --side long|short, --owner, optional: --size-usd, --collateral-usd, --rpc",
        },
        null,
        2
      )
    );
    process.exit(2);
  }
  return { market, side, sizeUsd, collateralUsd, owner, rpc };
}

(async () => {
  const args = parseArgs();
  const rpcUrl =
    args.rpc ??
    (process.env.HELIUS_API_KEY
      ? `https://rpc.helius.xyz/?api-key=${process.env.HELIUS_API_KEY}`
      : "https://api.mainnet-beta.solana.com");

  const connection = new Connection(rpcUrl, "processed");

  const marketKey = args.market.toUpperCase();
  const marketCfg = MARKETS[marketKey];
  if (!marketCfg) {
    console.log(
      JSON.stringify(
        {
          ok: false,
          error: "unknown-market",
          market: args.market,
          known: Object.keys(MARKETS),
        },
        null,
        2
      )
    );
    process.exit(1);
  }

  const owner = new PublicKey(args.owner);
  const programId = new PublicKey(PERPETUALS_PROGRAM_ID);
  const perpetualsPk = marketCfg.perpetuals
    ? new PublicKey(marketCfg.perpetuals)
    : PublicKey.findProgramAddressSync([Buffer.from("perpetuals")], programId)[0];
  const poolPk = new PublicKey(marketCfg.pool);
  const baseCustody = new PublicKey(marketCfg.baseCustody);
  const quoteCustody = new PublicKey(marketCfg.quoteCustody);
  const inputMint = new PublicKey(USDC_MINT);

  const custody = (args.side as Side) === "long" ? baseCustody : baseCustody;
  const collateralCustody = quoteCustody;

  const { position, positionRequest } = generatePositionAndPositionRequestPda({
    owner,
    pool: poolPk,
    perpetuals: perpetualsPk,
    programId,
    market: marketKey,
    side: args.side as Side,
    connection,
  });

  const positionRequestAta = getAssociatedTokenAddressSync(
    inputMint,
    positionRequest,
    true
  );

  const remaining = await remainingAccountsForCreateIncreasePositionMarketRequest({
    connection,
    programId,
    market: marketKey,
    side: args.side as Side,
    pool: poolPk,
    perpetuals: perpetualsPk,
    custody,
    collateralCustody,
    owner,
    position,
    positionRequest,
    positionRequestAta,
    inputMint,
    sizeUsd: args.sizeUsd,
    collateralUsd: args.collateralUsd,
  });

  const eventAuthority = marketCfg.eventAuthority
    ? marketCfg.eventAuthority
    : PublicKey.findProgramAddressSync([Buffer.from("__event_authority")], programId)[0].toBase58();

  const accounts = {
    owner: owner.toBase58(),
    fundingAccount: marketCfg.fundingAccount ?? null,
    perpetuals: perpetualsPk.toBase58(),
    pool: poolPk.toBase58(),
    position: position.toBase58(),
    positionRequest: positionRequest.toBase58(),
    positionRequestAta: positionRequestAta.toBase58(),
    custody: custody.toBase58(),
    collateralCustody: collateralCustody.toBase58(),
    inputMint: inputMint.toBase58(),
    referral: marketCfg.referral ?? owner.toBase58(),
    tokenProgram: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    associatedTokenProgram: "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
    systemProgram: "11111111111111111111111111111111",
    eventAuthority,
    program: PERPETUALS_PROGRAM_ID,
  };

  const payload = {
    ok: true,
    ix: "createIncreasePositionMarketRequest",
    params: {
      sizeUsdDelta: Math.round(args.sizeUsd * 1_000_000),
      collateralTokenDelta: Math.round(args.collateralUsd * 1_000_000),
      side: args.side,
      priceSlippage: 0,
      jupiterMinimumOut: null,
    },
    accounts,
    remainingAccounts: remaining,
    custodyPair: {
      custody: custody.toBase58(),
      collateralCustody: collateralCustody.toBase58(),
      inputMint: inputMint.toBase58(),
    },
  };

  console.log(JSON.stringify(payload, null, 2));
})().catch((e) => {
  console.error(
    JSON.stringify(
      { ok: false, error: "cli-crashed", message: String(e?.message ?? e) },
      null,
      2
    )
  );
  process.exit(1);
});
