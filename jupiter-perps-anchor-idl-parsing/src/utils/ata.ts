import {
  ASSOCIATED_TOKEN_PROGRAM_ID,
  TOKEN_PROGRAM_ID,
  TOKEN_2022_PROGRAM_ID,
  getAssociatedTokenAddressSync,
  createAssociatedTokenAccountIdempotentInstruction,
} from "@solana/spl-token";
import { PublicKey, TransactionInstruction } from "@solana/web3.js";

export function deriveAtaStrict(
  mint: PublicKey,
  owner: PublicKey,
  allowOwnerOffCurve = false,
  tokenProgramId: PublicKey = TOKEN_PROGRAM_ID,
): PublicKey {
  return getAssociatedTokenAddressSync(
    mint,
    owner,
    allowOwnerOffCurve,
    tokenProgramId,
    ASSOCIATED_TOKEN_PROGRAM_ID,
  );
}

export function createAtaIxStrict(
  payer: PublicKey,
  mint: PublicKey,
  owner: PublicKey,
  allowOwnerOffCurve = false,
  tokenProgramId: PublicKey = TOKEN_PROGRAM_ID,
): { ata: PublicKey; ix: TransactionInstruction } {
  const ata = deriveAtaStrict(mint, owner, allowOwnerOffCurve, tokenProgramId);
  const ix = createAssociatedTokenAccountIdempotentInstruction(
    payer,
    ata,
    owner,
    mint,
    tokenProgramId,
    ASSOCIATED_TOKEN_PROGRAM_ID,
  );
  return { ata, ix };
}

/**
 * Auto-detect the correct token program for a given mint by inspecting its owner.
 * Falls back to legacy TOKEN_PROGRAM_ID if the owner can't be fetched.
 */
export async function detectTokenProgramForMint(
  connection: import("@solana/web3.js").Connection,
  mint: PublicKey,
): Promise<PublicKey> {
  const info = await connection.getAccountInfo(mint);
  const owner = info?.owner;
  if (owner && (owner.equals(TOKEN_PROGRAM_ID) || owner.equals(TOKEN_2022_PROGRAM_ID))) {
    return owner;
  }
  return TOKEN_PROGRAM_ID;
}
