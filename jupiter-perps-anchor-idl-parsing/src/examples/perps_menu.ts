/**
 * Zero-argument interactive console menu for your perps workflow.
 * - Stores config in perps_menu.config.json on first run.
 * - Wrap WSOL, Open+Watch, Status, Watch-only, Dry-run Sim, Edit Config.
 * - Uses your existing example scripts via npx tsx.
 *
 * Run (double-clickable via the .bat below):
 *   npx --yes tsx C:\\sonic5\\jupiter-perps-anchor-idl-parsing\\src\\examples\\perps_menu.ts
 */

import { spawnSync } from "node:child_process";
import fs from "fs";
import readline from "readline";

// ─── CONSTANTS ──────────────────────────────────────────────────────────────────
const ROOT = "C:\\sonic5\\jupiter-perps-anchor-idl-parsing";
const EX = (p: string) => `${ROOT}\\src\\examples\\${p}`;
const CFG_PATH = `${ROOT}\\perps_menu.config.json`;

// Existing helper scripts you already created
const SCRIPTS = {
  open: EX("perps_open_market.ts"),
  watch: EX("perps_watch_position.ts"),             // your watcher variant that takes --position / --poll-ms
  readAcct: EX("perps_read_account.ts"),
  readWallet: EX("read_wallet_balances.ts"),
  wrap: EX("wrap_wsol.ts"),
  consoleHelper: EX("perps_console.ts"),            // optional: used for open-and-watch if you want
};

// Defaults that can be edited through "Edit Config"
const DEFAULT_CFG = {
  rpc: "https://api.mainnet-beta.solana.com",
  kp: "C:\\sonic5\\keys\\signer.txt",
  market: "SOL",
  side: "long",
  sizeUsd: 12,
  collat: 0.005,
  oraclePrice: 100,
  slip: 0.02,
  maxPrice: null as number | null,
  minPrice: null as number | null,
  position: "DQ9C3CR4npoYknxpq4UXsSZauwv1iJFZJ6bFdSfVXyjW",
  positionRequest: "6PdRkkqqFpedw8CNAQp3fyC9KX8s8qZVvmMPxhTGvWfp",
  walletAta: "CBq3eyJTtvu8tutaVupS92xMEypCKaAzUsZdTAHyVaBh",
  cuLimit: 800000,
  priorityMicrolamports: 2000,
  pollMs: 6000,
  timeoutS: 240,
  wethMint: "7vfCXTUXx5WJV5zvR6N1Wq3GzT2wP9Gd8Wmcj7iQg9s", // override here if your WETH differs
  wbtcMint: "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",
  usdcMint: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
};

// ─── UTIL: IO ───────────────────────────────────────────────────────────────────
function loadCfg() {
  try {
    if (fs.existsSync(CFG_PATH)) return JSON.parse(fs.readFileSync(CFG_PATH, "utf8"));
  } catch {}
  fs.writeFileSync(CFG_PATH, JSON.stringify(DEFAULT_CFG, null, 2), "utf8");
  return JSON.parse(JSON.stringify(DEFAULT_CFG));
}
function saveCfg(cfg: any) {
  fs.writeFileSync(CFG_PATH, JSON.stringify(cfg, null, 2), "utf8");
}

function ask(question: string): Promise<string> {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => rl.question(question, (ans) => { rl.close(); resolve(ans.trim()); }));
}

// Spawn helper
function run(label: string, scriptAbsPath: string, args: string[]) {
  console.log(`\n${"─".repeat(20)} ${label} ${"─".repeat(20)}`);
  const res = spawnSync("npx", ["--yes", "tsx", scriptAbsPath, ...args], { stdio: "inherit", shell: true });
  if (res.status !== 0) {
    console.log("❌ step failed");
  } else {
    console.log("✅ done");
  }
  return res.status ?? 1;
}

// ─── ACTIONS ────────────────────────────────────────────────────────────────────
async function actionStatus(cfg: any) {
  console.log("📊 Status snapshot");
  // Position decode
  run("Read Position", SCRIPTS.readAcct, ["--rpc", cfg.rpc, "--id", cfg.position, "--kind", "position"]);
  // Wallet balances
  const args = ["--rpc", cfg.rpc, "--kp", cfg.kp];
  if (cfg.wethMint) args.push("--weth-mint", String(cfg.wethMint));
  if (cfg.wbtcMint) args.push("--wbtc-mint", String(cfg.wbtcMint));
  if (cfg.usdcMint) args.push("--usdc-mint", String(cfg.usdcMint));
  run("Wallet Balances", SCRIPTS.readWallet, args);
}

async function actionWrap(cfg: any) {
  console.log("💧 Wrap WSOL");
  const amt = await ask(`Amount SOL to wrap (default 0.01): `);
  const amount = amt ? amt : "0.01";
  run("Wrap WSOL", SCRIPTS.wrap, [cfg.rpc, cfg.kp, amount]);
}

async function actionOpenAndWatch(cfg: any) {
  console.log("📈 Open & Watch");
  // Build open args inline so we depend only on perps_open_market.ts + perps_read_account.ts
  const openArgs = [
    "--rpc", cfg.rpc,
    "--kp", cfg.kp,
    "--market", cfg.market,
    "--side", cfg.side,
    "--size-usd", String(cfg.sizeUsd),
    "--collat", String(cfg.collat),
    "--position", cfg.position,
    "--position-request", cfg.positionRequest,
    "--cu-limit", String(cfg.cuLimit),
    "--priority-microlamports", String(cfg.priorityMicrolamports),
  ];
  if (cfg.oraclePrice != null && cfg.slip != null) {
    openArgs.push("--oracle-price", String(cfg.oraclePrice), "--slip", String(cfg.slip));
  } else if (cfg.maxPrice != null) {
    openArgs.push("--max-price", String(cfg.maxPrice));
  } else if (cfg.minPrice != null) {
    openArgs.push("--min-price", String(cfg.minPrice));
  }
  const r1 = run("Open Perp", SCRIPTS.open, openArgs);
  // Watch until filled
  console.log("\n⏱️  Watching position for fill… (Ctrl+C to stop)");
  // We reuse your perps_read_account.ts in a loop (so no dependency on the watcher flags style).
  const t0 = Date.now();
  const loopMs = Number(cfg.pollMs) || 6000;
  const timeoutMs = Number(cfg.timeoutS || 240) * 1000;

  while (true) {
    const r = spawnSync("npx", ["--yes", "tsx", SCRIPTS.readAcct, "--rpc", cfg.rpc, "--id", cfg.position, "--kind", "position"], { shell: true, encoding: "utf8" });
    if (r.stdout) {
      const m = r.stdout.match(/sizeUsd:\s*'(\d+)'/);
      if (m) {
        const sz = Number(m[1]);
        const elapsed = Math.floor((Date.now() - t0) / 1000);
        console.log(`🔎 sizeUsd=${sz}  elapsed=${elapsed}s`);
        if (sz > 0) { console.log("✅ filled"); break; }
      } else {
        process.stdout.write(r.stdout);
      }
    }
    if (Date.now() - t0 > timeoutMs) { console.log("⏳ timeout (no fill yet)"); break; }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, loopMs);
  }
}

async function actionDryRunSim(cfg: any) {
  console.log("🧪 Dry-run Simulate");
  const openArgs = [
    "--rpc", cfg.rpc,
    "--kp", cfg.kp,
    "--market", cfg.market,
    "--side", cfg.side,
    "--size-usd", String(cfg.sizeUsd),
    "--collat", String(cfg.collat),
    "--position", cfg.position,
    "--position-request", cfg.positionRequest,
    "--cu-limit", String(cfg.cuLimit),
    "--priority-microlamports", String(cfg.priorityMicrolamports),
    "--dry-run",
  ];
  if (cfg.oraclePrice != null && cfg.slip != null) {
    openArgs.push("--oracle-price", String(cfg.oraclePrice), "--slip", String(cfg.slip));
  } else if (cfg.maxPrice != null) {
    openArgs.push("--max-price", String(cfg.maxPrice));
  } else if (cfg.minPrice != null) {
    openArgs.push("--min-price", String(cfg.minPrice));
  }
  run("Simulate Open", SCRIPTS.open, openArgs);
}

async function actionWatchOnly(cfg: any) {
  console.log("👀 Watch Position");
  console.log("Press Ctrl+C to stop.");
  while (true) {
    const r = spawnSync("npx", ["--yes", "tsx", SCRIPTS.readAcct, "--rpc", cfg.rpc, "--id", cfg.position, "--kind", "position"], { shell: true, encoding: "utf8" });
    if (r.stdout) {
      const m = r.stdout.match(/sizeUsd:\s*'(\d+)'/);
      if (m) {
        const sz = Number(m[1]);
        console.log(`🔎 sizeUsd=${sz}`);
      } else {
        process.stdout.write(r.stdout);
      }
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, Number(cfg.pollMs) || 6000);
  }
}

async function actionEditConfig(cfg: any) {
  console.log("⚙️  Edit Config (Enter to keep current)");
  async function edit(key: string, hint?: string) {
    const cur = cfg[key];
    const ans = await ask(`${key}${hint ? ` (${hint})` : ""} [${cur}]: `);
    if (ans) {
      if (["sizeUsd","collat","oraclePrice","slip","maxPrice","minPrice","cuLimit","priorityMicrolamports","pollMs","timeoutS"].includes(key)) {
        const num = Number(ans);
        if (!Number.isNaN(num)) cfg[key] = num;
      } else {
        cfg[key] = ans;
      }
    }
  }
  await edit("rpc");
  await edit("kp");
  await edit("market", "SOL|ETH|BTC");
  await edit("side", "long|short");
  await edit("sizeUsd");
  await edit("collat");
  await edit("oraclePrice");
  await edit("slip");
  await edit("maxPrice");
  await edit("minPrice");
  await edit("position");
  await edit("positionRequest");
  await edit("walletAta");
  await edit("cuLimit");
  await edit("priorityMicrolamports");
  await edit("pollMs");
  await edit("timeoutS");
  await edit("usdcMint");
  await edit("wbtcMint");
  await edit("wethMint");
  saveCfg(cfg);
  console.log(`💾 Saved: ${CFG_PATH}`);
}

// ─── MENU ───────────────────────────────────────────────────────────────────────
function cls() { process.stdout.write("\x1Bc"); }

async function main() {
  const cfg = loadCfg();
  // Simple loop menu
  while (true) {
    cls();
    console.log("╔══════════════════════════════════════════════════════════════╗");
    console.log("║  🧭  Jupiter Perps Console                                   ║");
    console.log("║      rpc: ", cfg.rpc.padEnd(47, " "), "║");
    console.log("║      kp : ", cfg.kp.padEnd(47, " "), "║");
    console.log("║      pos: ", cfg.position.padEnd(47, " "), "║");
    console.log("╠══════════════════════════════════════════════════════════════╣");
    console.log("║  1) 📊  Status (Position + Wallet Balances)                  ║");
    console.log("║  2) 💧  Wrap WSOL                                            ║");
    console.log("║  3) 🚀  Open & Watch (uses current config)                   ║");
    console.log("║  4) 🧪  Dry-run Simulate (no send)                            ║");
    console.log("║  5) 👀  Watch Position (stream)                               ║");
    console.log("║  6) ⚙️   Edit Config                                          ║");
    console.log("║  7) ❌  Exit                                                 ║");
    console.log("╚══════════════════════════════════════════════════════════════╝");
    const choice = await ask("Select [1-7]: ");
    try {
      if (choice === "1") await actionStatus(cfg);
      else if (choice === "2") await actionWrap(cfg);
      else if (choice === "3") await actionOpenAndWatch(cfg);
      else if (choice === "4") await actionDryRunSim(cfg);
      else if (choice === "5") await actionWatchOnly(cfg);
      else if (choice === "6") await actionEditConfig(cfg);
      else if (choice === "7" || choice.toLowerCase() === "q") { console.log("Bye."); break; }
      else { console.log("🤷 Invalid choice."); }
    } catch (e: any) {
      console.error("💥 Error:", e?.message || e);
    }
    await ask("\nPress Enter to return to menu...");
  }
}

main();
