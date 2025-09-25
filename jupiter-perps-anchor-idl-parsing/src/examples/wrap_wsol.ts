import { Connection, Keypair, SystemProgram, Transaction, sendAndConfirmTransaction } from "@solana/web3.js";
import { getAssociatedTokenAddressSync, createAssociatedTokenAccountIdempotentInstruction, createSyncNativeInstruction, NATIVE_MINT } from "@solana/spl-token";
import fs from "fs";

const RPC = process.argv[2];                // e.g. https://api.mainnet-beta.solana.com
const KP_PATH = process.argv[3];            // e.g. C:\sonic5\keys\signer.txt
const AMOUNT_SOL = parseFloat(process.argv[4] || "0.005"); // how much SOL to wrap

if (!RPC || !KP_PATH) {
  console.error("Usage: tsx wrap_wsol.ts <rpc> <keypair_path> [amount_sol]");
  process.exit(1);
}

const secret = fs.readFileSync(KP_PATH, "utf8").trim();
const kp = Keypair.fromSecretKey(
  secret.startsWith("[") ? Uint8Array.from(JSON.parse(secret)) : Buffer.from(secret, "base64")
);

(async () => {
  const conn = new Connection(RPC, "confirmed");
  const owner = kp.publicKey;
  const ata = getAssociatedTokenAddressSync(NATIVE_MINT, owner, false);

  const lamports = Math.round(AMOUNT_SOL * 1e9);
  const tx = new Transaction().add(
    createAssociatedTokenAccountIdempotentInstruction(owner, ata, owner, NATIVE_MINT),
    SystemProgram.transfer({ fromPubkey: owner, toPubkey: ata, lamports }),
    createSyncNativeInstruction(ata)
  );

  const sig = await sendAndConfirmTransaction(conn, tx, [kp]);
  console.log("✅ Wrapped SOL to WSOL ATA:", ata.toBase58());
  console.log("   Amount:", AMOUNT_SOL, "SOL");
  console.log("   Sig   :", sig);
})();
