/**
 * One-command console driver for your perps flow.
 * Actions:
 *   - open-and-watch  (optional wrap) -> open -> watch until filled (or timeout)
 *   - status          (snapshot: position + wallet WSOL ATA)
 *   - wrap            (wrap WSOL only)
 *
 * Usage examples:
 *   npx --yes tsx C:\sonic5\jupiter-perps-anchor-idl-parsing\src\examples\perps_console.ts open-and-watch ^
 *     --rpc https://api.mainnet-beta.solana.com ^
 *     --kp C:\sonic5\keys\signer.txt ^
 *     --market SOL --side long --size-usd 12 --collat 0.005 ^
 *     --oracle-price 100 --slip 0.02 ^
 *     --position DQ9C3CR4npoYknxpq4UXsSZauwv1iJFZJ6bFdSfVXyjW ^
 *     --position-request 6PdRkkqqFpedw8CNAQp3fyC9KX8s8qZVvmMPxhTGvWfp ^
 *     --maybe-wrap 0      --poll-ms 6000 --timeout-s 240 --cu-limit 800000 --priority-microlamports 2000
 *
 *   npx --yes tsx C:\sonic5\jupiter-perps-anchor-idl-parsing\src\examples\perps_console.ts status ^
 *     --rpc https://api.mainnet-beta.solana.com ^
 *     --position DQ9C3CR4npoYknxpq4UXsSZauwv1iJFZJ6bFdSfVXyjW ^
 *     --wallet-ata CBq3eyJTtvu8tutaVupS92xMEypCKaAzUsZdTAHyVaBh
 */

import { spawnSync } from "node:child_process";
import yargs from "yargs";
import { hideBin } from "yargs/helpers";

const ROOT = "C:\\sonic5\\jupiter-perps-anchor-idl-parsing";
const EX = (p: string) => `${ROOT}\\src\\examples\\${p}`;

function runTsx(scriptAbsPath: string, args: string[], label: string) {
  console.log(`\n──────────────────────── ${label} ────────────────────────`);
  const res = spawnSync("npx", ["--yes", "tsx", scriptAbsPath, ...args], {
    stdio: "inherit",
    shell: true
  });
  if (res.status !== 0) {
    process.exitCode = res.status ?? 1;
    console.error(`\n❌ Step failed: ${label}`);
    process.exit(process.exitCode);
  }
}

const argv = await yargs(hideBin(process.argv))
  .command("open-and-watch", "Optional wrap -> open -> watch until filled", (y) =>
    y
      .option("rpc", { type: "string", demandOption: true })
      .option("kp", { type: "string", demandOption: true, desc: "Keypair file (JSON array)" })
      .option("market", { type: "string", choices: ["SOL", "ETH", "BTC"], demandOption: true })
      .option("side", { type: "string", choices: ["long", "short"], demandOption: true })
      .option("size-usd", { type: "number", demandOption: true })
      .option("collat", { type: "number", default: 0 })
      .option("oracle-price", { type: "number" })
      .option("slip", { type: "number" })
      .option("max-price", { type: "number" })
      .option("min-price", { type: "number" })
      .option("position", { type: "string", demandOption: true })
      .option("position-request", { type: "string", demandOption: true })
      .option("maybe-wrap", { type: "number", default: 0, desc: "If >0, wrap this much SOL first" })
      .option("cu-limit", { type: "number", default: 800_000 })
      .option("priority-microlamports", { type: "number", default: 2000 })
      .option("poll-ms", { type: "number", default: 6000 })
      .option("timeout-s", { type: "number", default: 240 })
      .option("wallet-ata", { type: "string", desc: "Optional WSOL ATA for status print" })
  )
  .command("status", "Snapshot: position + wallet WSOL ATA", (y) =>
    y
      .option("rpc", { type: "string", demandOption: true })
      .option("position", { type: "string", demandOption: true })
      .option("wallet-ata", { type: "string", demandOption: true })
  )
  .command("wrap", "Wrap WSOL only", (y) =>
    y
      .option("rpc", { type: "string", demandOption: true })
      .option("kp", { type: "string", demandOption: true })
      .option("amount", { type: "number", demandOption: true })
  )
  .demandCommand(1)
  .strict()
  .help().argv;

const [cmd] = argv._;

if (cmd === "wrap") {
  // Wrap WSOL once
  runTsx(EX("wrap_wsol.ts"), [argv.rpc as string, argv.kp as string, String(argv.amount)], "Wrap WSOL");
  process.exit(0);
}

if (cmd === "status") {
  // Read Position
  runTsx(
    EX("perps_read_account.ts"),
    ["--rpc", argv.rpc as string, "--id", argv.position as string, "--kind", "position"],
    "Read Position"
  );
  // Read wallet ATA
  runTsx(
    EX("read_token_account.ts"),
    ["--rpc", argv.rpc as string, "--ata", argv["wallet-ata"] as string],
    "Read Wallet WSOL ATA"
  );
  process.exit(0);
}

if (cmd === "open-and-watch") {
  const rpc = argv.rpc as string;

  // 1) maybe wrap
  const maybeWrapAmt = Number(argv["maybe-wrap"] || 0);
  if (maybeWrapAmt > 0) {
    runTsx(EX("wrap_wsol.ts"), [rpc, argv.kp as string, String(maybeWrapAmt)], "Wrap WSOL (optional)");
  }

  // 2) open (with guardrails + priority)
  const openArgs: string[] = [
    "--rpc", rpc,
    "--kp", argv.kp as string,
    "--market", argv.market as string,
    "--side", argv.side as string,
    "--size-usd", String(argv["size-usd"]),
    "--collat", String(argv.collat ?? 0),
    "--position", argv.position as string,
    "--position-request", argv["position-request"] as string,
    "--cu-limit", String(argv["cu-limit"]),
    "--priority-microlamports", String(argv["priority-microlamports"]),
  ];

  if (argv["oracle-price"] != null && argv["slip"] != null) {
    openArgs.push("--oracle-price", String(argv["oracle-price"]), "--slip", String(argv.slip));
  } else if (argv["max-price"] != null) {
    openArgs.push("--max-price", String(argv["max-price"]));
  } else if (argv["min-price"] != null) {
    openArgs.push("--min-price", String(argv["min-price"]));
  }

  runTsx(EX("perps_open_market.ts"), openArgs, "Open Perp");

  // 3) watch (poll until sizeUsd > 0 or timeout)
  // Your watcher uses --position and --poll-ms (NOT id/timeout/interval)
  const deadlineMs = Number(argv["timeout-s"]) * 1000;
  const pollMs = Number(argv["poll-ms"]);
  const t0 = Date.now();

  console.log("\n──────────────────────── Watch Position ────────────────────────");
  for (;;) {
    // snapshot once
    const readRes = spawnSync(
      "npx",
      ["--yes", "tsx", EX("perps_read_account.ts"), "--rpc", rpc, "--id", argv.position as string, "--kind", "position"],
      { encoding: "utf8", shell: true }
    );
    if (readRes.status !== 0) {
      process.stdout.write(readRes.stdout || "");
      process.stderr.write(readRes.stderr || "");
      console.error("❌ Read failed; stopping.");
      process.exit(readRes.status ?? 1);
    }
    const out = (readRes.stdout || "").toString();
    // naive check: look for "sizeUsd: '0'" vs non-zero — we printed as strings
    const m = out.match(/sizeUsd:\s*'(\d+)'/);
    if (m) {
      const size = Number(m[1]);
      console.log(`🔎 sizeUsd=${size}  (elapsed ${Math.floor((Date.now()-t0)/1000)}s)`);
      if (size > 0) {
        console.log("✅ filled");
        break;
      }
    } else {
      console.log("ℹ️  sizeUsd not found in decode (IDL changed?); showing raw output below:");
      console.log(out);
    }

    if (Date.now() - t0 > deadlineMs) {
      console.log("⏳ timeout: position not filled yet");
      break;
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, pollMs); // sleep
  }

  // 4) optional quick status
  if (argv["wallet-ata"]) {
    runTsx(
      EX("read_token_account.ts"),
      ["--rpc", rpc, "--ata", argv["wallet-ata"] as string],
      "Wallet WSOL ATA"
    );
  }

  process.exit(0);
}

// Fallback (shouldn’t happen)
console.error("Unknown command.");
process.exit(1);
