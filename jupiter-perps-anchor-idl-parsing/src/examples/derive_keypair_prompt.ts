import fs from "fs";
import path from "path";
import * as bip39 from "bip39";
import { derivePath } from "ed25519-hd-key";
import nacl from "tweetnacl";
import { Keypair } from "@solana/web3.js";
import readline from "readline";

// ---- config you can tweak (or leave as-is) ----
const OUTFILE = "C:\\sonic5\\keys\\signer.txt";
const ACCOUNT_INDEX = 0; // m/44'/501'/{ACCOUNT_INDEX}'/{CHANGE_INDEX}'
const CHANGE_INDEX = 0;  // usually 0; try 1 if your wallet uses it

// Hidden prompt helper
async function promptHidden(question: string): Promise<string> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const origWrite = (rl as any)._writeToOutput;
  (rl as any)._writeToOutput = function (_str: string) {
    // mask user input with '*'
    if ((rl as any).stdoutMuted) ((rl as any).output as any).write("*");
    else (origWrite as any).apply(rl, arguments as any);
  };
  (rl as any).stdoutMuted = true;
  const answer: string = await new Promise((resolve) =>
    rl.question(question, (ans) => resolve(ans))
  );
  (rl as any).stdoutMuted = false;
  rl.close();
  console.log(); // newline after masked input
  return answer.trim().replace(/\s+/g, " ");
}

(async () => {
  console.log("🔐 Derive Solana keypair from mnemonic (nothing is uploaded; local only).");
  console.log("    Path:", `m/44'/501'/${ACCOUNT_INDEX}'/${CHANGE_INDEX}'`);
  const mnemonic = await promptHidden("Paste your 12/24-word seed phrase: ");

  if (!bip39.validateMnemonic(mnemonic)) {
    console.error("❌ Invalid BIP39 mnemonic. Check spacing and words.");
    process.exit(1);
  }

  const seed = bip39.mnemonicToSeedSync(mnemonic); // Buffer
  const pathStr = `m/44'/501'/${ACCOUNT_INDEX}'/${CHANGE_INDEX}'`;
  const { key } = derivePath(pathStr, seed.toString("hex")); // 32-byte ed25519 seed
  const kp = Keypair.fromSecretKey(nacl.sign.keyPair.fromSeed(key).secretKey);

  fs.mkdirSync(path.dirname(OUTFILE), { recursive: true });
  fs.writeFileSync(OUTFILE, `[${Array.from(kp.secretKey).toString()}]`, { encoding: "utf8" });

  console.log("✅ Wrote keypair JSON:", OUTFILE);
  console.log("🔑 Public key        :", kp.publicKey.toBase58());
  console.log("⚠️  Keep this file private. Anyone with it can sign.");
})();
