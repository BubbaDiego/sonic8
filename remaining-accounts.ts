import type { Connection, PublicKey } from "@solana/web3.js";

import type { RemainingAccount, Side } from "./types.js";

export type RemainingAccountsArgs = {
  connection: Connection;
  programId: PublicKey;
  market: string;
  side: Side;
  pool: PublicKey;
  perpetuals: PublicKey;
  custody: PublicKey;
  collateralCustody: PublicKey;
  owner: PublicKey;
  position: PublicKey;
  positionRequest: PublicKey;
  positionRequestAta: PublicKey;
  inputMint: PublicKey;
  sizeUsd?: number;
  collateralUsd?: number;
};

export async function remainingAccountsForCreateIncreasePositionMarketRequest(
  _args: RemainingAccountsArgs
): Promise<RemainingAccount[]> {
  // The current IDL enumerates all required accounts for the request. Any
  // additional accounts (e.g. dynamic oracles) can be appended here if the
  // upstream helpers expose them in the future. For now we return an empty
  // array, signalling that no extra accounts are required beyond the IDL list.
  return [];
}
