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
  const arr: number[] = JSON.parse(raw);
  return Keypair.fromSecretKey(Uint8Array.from(arr));
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

function padRight(s: string, n: number) { return (s + " ".repeat(n)).slice(0, n); }

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

  console.log("Owner:", owner.toBase58());
  console.log("");
  console.log(padRight("Asset", 8), padRight("Mint", 45), padRight("ATA", 44), padRight("UI Balance", 14), "State");
  console.log("-".repeat(8), "-".repeat(45), "-".repeat(44), "-".repeat(14), "-----");
  console.log(
    padRight("SOL", 8),
    padRight("-", 45),
    padRight("-", 44),
    padRight(sol.toFixed(9), 14),
    "wallet"
  );
  function printRow(name: string, mint: string, r: ReturnType<typeof safeTokenBalance> extends Promise<infer T> ? T : never) {
    console.log(
      padRight(name, 8),
      padRight(mint, 45),
      padRight(r.ata.toBase58(), 44),
      padRight(r.ui.toFixed(r.decimals > 6 ? 6 : r.decimals || 0), 14),
      r.exists ? "initialized" : "missing"
    );
  }
  printRow("WSOL", mints.WSOL, wsol);
  printRow("USDC", mints.USDC, usdc);
  printRow("WBTC", mints.WBTC, wbtc);
  printRow("WETH", mints.WETH, weth);

  console.log("\nNotes:");
  console.log("• If a row says 'missing', that ATA hasn’t been created yet (balance = 0).");
  console.log("• Override mints with --usdc-mint / --wbtc-mint / --weth-mint if you use different tokens.");
})();
