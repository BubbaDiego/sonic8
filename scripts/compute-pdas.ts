import { PublicKey } from "@solana/web3.js";
import BN from "bn.js";

/**
 * Jupiter Perps program id (mainnet)
 * https://station.jup.ag/guides/perpetual-exchange/onchain-accounts
 */
const JUPITER_PERPS_PROGRAM_ID = new PublicKey("PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu");

/**
 * Derive the Position PDA exactly like Anchor expects.
 * seeds = [
 *   "position",
 *   wallet,
 *   pool,
 *   custody,             // BASE custody (e.g., SOL custody for SOL-PERP)
 *   collateralCustody,   // QUOTE custody (e.g., USDC custody)
 *   sideByte             // [1] = long, [2] = short
 * ]
 */
function derivePositionPda(
  wallet: PublicKey,
  pool: PublicKey,
  custody: PublicKey,
  collateralCustody: PublicKey,
  side: "long" | "short",
) {
  const sideByte = side === "long" ? [1] : [2];
  const [pda] = PublicKey.findProgramAddressSync(
    [
      Buffer.from("position"),
      wallet.toBuffer(),
      pool.toBuffer(),
      custody.toBuffer(),
      collateralCustody.toBuffer(),
      Buffer.from(sideByte),
    ],
    JUPITER_PERPS_PROGRAM_ID,
  );
  return pda;
}

/**
 * Derive the PositionRequest PDA (increase/decrease):
 * seeds = [
 *   "position_request",
 *   positionPubkey,
 *   counter (u64 little-endian),
 *   requestChangeByte       // [1] = increase, [2] = decrease
 * ]
 */
function derivePositionRequestPda(
  position: PublicKey,
  requestChange: "increase" | "decrease",
  counter?: BN, // if omitted, you can supply any u64 you want later on-chain
) {
  const requestChangeByte = requestChange === "increase" ? [1] : [2];
  const c = counter ?? new BN(0); // default 0 for deterministic output
  const counterLe = c.toArrayLike(Buffer, "le", 8);
  const [pda] = PublicKey.findProgramAddressSync(
    [
      Buffer.from("position_request"),
      position.toBuffer(),
      counterLe,
      Buffer.from(requestChangeByte),
    ],
    JUPITER_PERPS_PROGRAM_ID,
  );
  return { positionRequest: pda, counter: c };
}

/** CLI */
function getArg(name: string, fallback?: string) {
  const i = process.argv.indexOf(`--${name}`);
  if (i >= 0 && i + 1 < process.argv.length) return process.argv[i + 1];
  return fallback;
}

(async () => {
  const wallet58 = getArg("wallet")!;
  const pool58 = getArg("pool")!;
  const custody58 = getArg("custody")!; // BASE custody (e.g., SOL)
  const collateral58 = getArg("collateral")!; // QUOTE custody (e.g., USDC)
  const sideStr = (getArg("side", "long") as "long" | "short") || "long";

  const changeStr = (getArg("change", "increase") as "increase" | "decrease") || "increase";
  const counterStr = getArg("counter"); // optional u64 string
  const counterBN = counterStr ? new BN(counterStr, 10) : undefined;

  const wallet = new PublicKey(wallet58);
  const pool = new PublicKey(pool58);
  const custody = new PublicKey(custody58);
  const collateral = new PublicKey(collateral58);

  const position = derivePositionPda(wallet, pool, custody, collateral, sideStr);
  const { positionRequest, counter } = derivePositionRequestPda(position, changeStr, counterBN);

  console.log(
    JSON.stringify(
      {
        programId: JUPITER_PERPS_PROGRAM_ID.toBase58(),
        inputs: {
          wallet: wallet58,
          pool: pool58,
          custody: custody58,
          collateral: collateral58,
          side: sideStr,
          change: changeStr,
          counter: counter.toString(),
        },
        outputs: {
          position: position.toBase58(),
          positionRequest: positionRequest.toBase58(),
        },
      },
      null,
      2,
    ),
  );
})();
