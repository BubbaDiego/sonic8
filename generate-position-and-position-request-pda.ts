import { PublicKey } from "@solana/web3.js";
import { createHash } from "crypto";

import { MARKETS } from "./perps_constants.js";

export type GeneratePositionPdaArgs = {
  owner: PublicKey;
  pool: PublicKey;
  perpetuals: PublicKey;
  programId: PublicKey;
  market: string;
  side?: "long" | "short";
  connection?: unknown;
};

function seed32(source: Buffer | Uint8Array | string): Buffer {
  if (Buffer.isBuffer(source)) {
    if (source.length > 32) {
      throw new Error(`seed too long (${source.length}B > 32B)`);
    }
    return source;
  }
  if (typeof source !== "string") {
    return Buffer.from(source);
  }
  try {
    const pk = new PublicKey(source);
    return pk.toBuffer();
  } catch (err) {
    return createHash("sha256").update(source, "utf8").digest().subarray(0, 32);
  }
}

export function generatePositionAndPositionRequestPda(
  args: GeneratePositionPdaArgs
): { position: PublicKey; positionRequest: PublicKey } {
  const owner = args.owner;
  const programId = args.programId;
  const marketKey = args.market.toUpperCase();
  const marketCfg = MARKETS[marketKey];
  const marketMint = marketCfg?.baseMint ?? marketCfg?.quoteMint ?? args.market;
  const seed = seed32(marketMint ?? marketKey);

  const position = PublicKey.findProgramAddressSync(
    [Buffer.from("position"), owner.toBuffer(), seed],
    programId
  )[0];

  const positionRequest = PublicKey.findProgramAddressSync(
    [Buffer.from("position-request"), owner.toBuffer(), seed],
    programId
  )[0];

  return { position, positionRequest };
}
