import { Connection, Keypair, PublicKey } from "@solana/web3.js";
import {
  getAssociatedTokenAddressSync,
  getAccount,
  getMint,
  NATIVE_MINT
} from "@solana/spl-token";
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import fs from "fs";
import bs58 from "bs58";

// Defaults (override via CLI if you use different mints)
const DEFAULT_USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"; // USDC
const DEFAULT_WBTC = "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E"; // Wormhole BTC
// Common WETH (Wormhole ETH) mint on Solana. If yours differs, pass --weth-mint
const DEFAULT_WETH = "7vfCXTUXx5WJV5zvR6N1Wq3GzT2wP9Gd8Wmcj7iQg9s"; // fallback; override if needed

const argv = await yargs(hideBin(process.argv))
  .option("rpc", { type: "string", demandOption: true, desc: "RPC URL" })
  .option("kp",  { type: "string", demandOption: true, desc: "Path to keypair JSON (array of 64 bytes)" })
  .option("usdc-mint", { type: "string", default: DEFAULT_USDC })
  .option("wbtc-mint", { type: "string", default: DEFAULT_WBTC })
  .option("weth-mint", { type: "string", default: DEFAULT_WETH })
  .help().strict().argv;

function loadKeypair(p: string): Keypair {
  const raw = fs.readFileSync(p, "utf8").trim();

  // JSON array (Solana CLI format)
  if (raw.startsWith("[")) {
    const arr: number[] = JSON.parse(raw);
    return Keypair.fromSecretKey(Uint8Array.from(arr));
  }

  // Looks like a mnemonic? (spaces + words) — refuse with a helpful message
  if (/\s/.test(raw) && !/^[\[{]/.test(raw)) {
    throw new Error(
      "Key file looks like a mnemonic. Run derive_keypair_prompt.ts to produce signer.txt (JSON array) first."
    );
  }

  // Base58 secret (common export)
  if (/^[1-9A-HJ-NP-Za-km-z]+$/.test(raw)) {
    const bytes = bs58.decode(raw);
    if (bytes.length === 64) return Keypair.fromSecretKey(bytes);
    if (bytes.length === 32) {
      throw new Error(
        "Base58 decodes to 32 bytes (seed), not a 64-byte secretKey. Convert to a JSON keypair first."
      );
    }
    throw new Error(`Base58 decoded to ${bytes.length} bytes; expected 64.`);
  }

  // Base64 fallback
  try {
    const b = Buffer.from(raw, "base64");
    if (b.length === 64) return Keypair.fromSecretKey(Uint8Array.from(b));
  } catch {}

  throw new Error(
    "Unrecognized key format. Provide JSON array, base58 64-byte secret, or base64 64-byte secret."
  );
}

async function safeTokenBalance(
  connection: Connection,
  owner: PublicKey,
  mint: PublicKey
): Promise<{ ata: PublicKey; amountRaw: bigint; ui: number; decimals: number; exists: boolean }> {
  const ata = getAssociatedTokenAddressSync(mint, owner, false);
  try {
    const acc = await getAccount(connection, ata);
    const mintInfo = await getMint(connection, acc.mint);
    const ui = Number(acc.amount) / 10 ** mintInfo.decimals;
    return { ata, amountRaw: acc.amount, ui, decimals: mintInfo.decimals, exists: true };
  } catch {
    // not created yet
    const mintInfo = await getMint(connection, mint).catch(() => null);
    const dec = mintInfo ? mintInfo.decimals : 0;
    return { ata, amountRaw: 0n, ui: 0, decimals: dec, exists: false };
  }
}

(async () => {
  const connection = new Connection(argv.rpc, "confirmed");
  const kp = loadKeypair(argv.kp);
  const owner = kp.publicKey;

  // SOL (lamports)
  const lamports = await connection.getBalance(owner, { commitment: "confirmed" });
  const sol = lamports / 1e9;

  // Tokens
  const mints = {
    WSOL: NATIVE_MINT.toBase58(),
    USDC: argv["usdc-mint"]!,
    WBTC: argv["wbtc-mint"]!,
    WETH: argv["weth-mint"]!
  };

  const [wsol, usdc, wbtc, weth] = await Promise.all([
    safeTokenBalance(connection, owner, NATIVE_MINT),
    safeTokenBalance(connection, owner, new PublicKey(mints.USDC)),
    safeTokenBalance(connection, owner, new PublicKey(mints.WBTC)),
    safeTokenBalance(connection, owner, new PublicKey(mints.WETH))
  ]);

  const RESET = "\x1b[0m", GREEN = "\x1b[32m", DIM = "\x1b[2m";
  function short(s: string) { return s && s.length > 10 ? `${s.slice(0, 4)}…${s.slice(-4)}` : s; }
  function padRight(s: string, n: number) { return (s + " ".repeat(n)).slice(0, n); }
  function tint(amount: number, text: string) {
    return amount > 0 ? `${GREEN}${text}${RESET}` : `${DIM}${text}${RESET}`;
  }

  console.log("Owner:", owner.toBase58(), "\n");
  console.log(padRight("Asset", 8), padRight("Mint", 14), padRight("ATA", 14), padRight("UI Balance", 14), "State");
  console.log("-".repeat(8), "-".repeat(14), "-".repeat(14), "-".repeat(14), "-----");

  console.log(
    padRight("SOL", 8),
    padRight("-", 14),
    padRight("-", 14),
    tint(sol, padRight(sol.toFixed(9), 14)),
    "wallet"
  );

  function row(name: string, mint: string, r: any) {
    const uiStr = r.ui.toFixed(r.decimals > 6 ? 6 : r.decimals || 0);
    console.log(
      padRight(name, 8),
      padRight(short(mint), 14),
      padRight(short(r.ata.toBase58()), 14),
      tint(r.ui, padRight(uiStr, 14)),
      r.exists ? "initialized" : "missing"
    );
  }
  row("WSOL", mints.WSOL, wsol);
  row("USDC", mints.USDC, usdc);
  row("WBTC", mints.WBTC, wbtc);
  row("WETH", mints.WETH, weth);

  console.log("\nNotes:");
  console.log("• IDs shortened as AAAA…ZZZZ. Use script source if you need full values.");
  console.log("• Override mints with --usdc-mint / --wbtc-mint / --weth-mint if you use different tokens.");
})();
