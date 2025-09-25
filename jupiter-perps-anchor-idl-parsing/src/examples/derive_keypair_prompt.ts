import fs from "fs";
import path from "path";
import * as bip39 from "bip39";
import { derivePath } from "ed25519-hd-key";
import nacl from "tweetnacl";
import { Keypair } from "@solana/web3.js";
import readline from "readline";

// ---- config (change if you like) ----
const OUTFILE = "C:\\sonic5\\keys\\signer.txt";

function rl() {
  return readline.createInterface({ input: process.stdin, output: process.stdout });
}

async function prompt(question: string, mask = false): Promise<string> {
  const r = rl();
  const orig = (r as any)._writeToOutput;
  if (mask) {
    (r as any)._writeToOutput = function (_str: string) {
      (r.output as any).write("*");
    };
  }
  const ans: string = await new Promise((resolve) => r.question(question, resolve));
  (r as any)._writeToOutput = orig;
  r.close();
  console.log();
  return ans;
}

function normalizeMnemonic(raw: string): string {
  // Replace punctuation with spaces, collapse whitespace, trim, lowercase ASCII
  return raw
    .replace(/[\u2018\u2019\u201C\u201D]/g, "'")           // fancy quotes -> straight (just in case)
    .replace(/[,.\.;:\u00A0\u2000-\u200B]/g, " ")          // commas/periods/non-breaking/zero-width -> space
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

(async () => {
  console.log("🔐 Derive Solana keypair from mnemonic (local only).");
  console.log("    Default path: m/44'/501'/0'/0' (you can change below)");

  // 1) Mnemonic (masked input)
  const rawMnemonic = await prompt("Paste your 12/24-word seed phrase: ", true);
  const mnemonic = normalizeMnemonic(rawMnemonic);
  const words = mnemonic ? mnemonic.split(" ") : [];
  console.log(`   • normalized word count: ${words.length}`);

  if (!(words.length === 12 || words.length === 24)) {
    console.error("❌ Expected 12 or 24 words after normalization.");
    process.exit(1);
  }
  if (!bip39.validateMnemonic(mnemonic)) {
    console.error("❌ Invalid BIP-39 mnemonic (word list or checksum). Double-check spelling and spaces.");
    process.exit(1);
  }

  // 2) Optional BIP-39 passphrase (not your seed words; some wallets call this a “25th word”)
  const maybePass = await prompt("Optional BIP-39 passphrase (enter to skip): ", true);
  const bip39Passphrase = maybePass.length ? maybePass : undefined;

  // 3) Path indices (press Enter to accept defaults)
  const accStr = await prompt("Account index (default 0): ");
  const chgStr = await prompt("Change index  (default 0): ");
  const account = accStr.trim() ? parseInt(accStr, 10) : 0;
  const change = chgStr.trim() ? parseInt(chgStr, 10) : 0;
  if (Number.isNaN(account) || Number.isNaN(change)) {
    console.error("❌ Indices must be integers.");
    process.exit(1);
  }

  const pathStr = `m/44'/501'/${account}'/${change}'`;
  console.log("   • using path:", pathStr);

  // 4) Derive and write
  const seed = await bip39.mnemonicToSeed(mnemonic, bip39Passphrase); // respects passphrase if provided
  const { key } = derivePath(pathStr, Buffer.from(seed).toString("hex")); // 32-byte ed25519 seed
  const kp = Keypair.fromSecretKey(nacl.sign.keyPair.fromSeed(key).secretKey);

  fs.mkdirSync(path.dirname(OUTFILE), { recursive: true });
  fs.writeFileSync(OUTFILE, `[${Array.from(kp.secretKey).toString()}]`, { encoding: "utf8" });

  console.log("✅ Wrote keypair JSON:", OUTFILE);
  console.log("🔑 Public key        :", kp.publicKey.toBase58());
  console.log("⚠️  Keep this file private.");
})();
