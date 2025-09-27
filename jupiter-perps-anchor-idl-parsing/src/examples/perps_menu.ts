/**
 * Zero-argument interactive console menu for your perps workflow.
 * - Stores config in perps_menu.config.json on first run.
 * - Wrap WSOL, Open+Watch, Status, Watch-only, Dry-run Sim, Edit Config.
 * - Uses your existing example scripts via npx tsx.
 *
 * Run (double-clickable via the .bat below):
 *   npx --yes tsx C:\\sonic5\\jupiter-perps-anchor-idl-parsing\\src\\examples\\perps_menu.ts
 */

import { spawn, spawnSync } from "node:child_process";
import fs from "fs";
import { Connection, PublicKey, Keypair } from "@solana/web3.js";
import {
  getAssociatedTokenAddressSync,
  getAccount,
  getMint,
  NATIVE_MINT,
} from "@solana/spl-token";
import readline from "readline";

// ─── CONSTANTS ──────────────────────────────────────────────────────────────────
const ROOT = "C:\\sonic5\\jupiter-perps-anchor-idl-parsing";
const EX = (p: string) => `${ROOT}\\src\\examples\\${p}`;
const CFG_PATH = `${ROOT}\\perps_menu.config.json`;

const RESET = "\x1b[0m",
  GREEN = "\x1b[32m",
  DIM = "\x1b[2m";

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
  rpcList: [
    "https://api.mainnet-beta.solana.com"
  ],
  rpcIndex: 0,
  kp: "C:\\sonic5\\keys\\signer.txt",
  market: "SOL",
  side: "long",
  sizeUsd: 12,
  collat: 0.005,
  collatMint: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
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

// Stream child stdout/stderr to console AND capture into a string buffer.
async function runTee(label: string, scriptAbsPath: string, args: string[]) {
  return await new Promise<{ status: number; combined: string }>((resolve) => {
    const child = spawn("npx", ["--yes", "tsx", scriptAbsPath, ...args], { shell: true });
    let combined = "";
    child.stdout.on("data", (d) => { const s = d.toString(); combined += s; process.stdout.write(s); });
    child.stderr.on("data", (d) => { const s = d.toString(); combined += s; process.stderr.write(s); });
    child.on("close", (code) => resolve({ status: code ?? 1, combined }));
  });
}

// ——— PDA auto-align helpers ———
function shortId(s: string) {
  return s && s.length > 10 ? `${s.slice(0, 4)}…${s.slice(-4)}` : s;
}
function color(amount: number, s: string) {
  return amount > 0 ? `${GREEN}${s}${RESET}` : `${DIM}${s}${RESET}`;
}

async function getBalancesInline(
  cfg: any
): Promise<{ sol: number; wsol: number; collat: number; collatSym: string }> {
  const conn = new Connection(cfg.rpc, "confirmed");
  const arr: number[] = JSON.parse(fs.readFileSync(cfg.kp, "utf8"));
  const secret = Uint8Array.from(arr);
  let ownerPk: PublicKey;
  try {
    const maybeFromSeed = (PublicKey as any).fromSeed as ((seed: Uint8Array) => PublicKey) | undefined;
    ownerPk = maybeFromSeed ? maybeFromSeed(secret.slice(0, 32)) : Keypair.fromSecretKey(secret).publicKey;
  } catch {
    ownerPk = Keypair.fromSecretKey(secret).publicKey;
  }

  const lamports = await conn.getBalance(ownerPk).catch(() => 0);
  const sol = lamports / 1e9;

  const wsolAta = getAssociatedTokenAddressSync(NATIVE_MINT, ownerPk, false);
  const wsolAcc = await getAccount(conn, wsolAta).catch(() => null);
  const wsolDec = (await getMint(conn, NATIVE_MINT).catch(() => ({ decimals: 9 } as any))).decimals ?? 9;
  const wsol = wsolAcc ? Number(wsolAcc.amount) / 10 ** wsolDec : 0;

  const collatMint = cfg.collatMint ? new PublicKey(cfg.collatMint) : NATIVE_MINT;
  const collatSym = cfg.collatMint ? "coll" : "wsol";
  const collAta = getAssociatedTokenAddressSync(collatMint, ownerPk, false);
  const collAcc = await getAccount(conn, collAta).catch(() => null);
  const collDec = (await getMint(conn, collatMint).catch(() => ({ decimals: 6 } as any))).decimals ?? 6;
  const coll = collAcc ? Number(collAcc.amount) / 10 ** collDec : 0;

  return { sol, wsol, collat: coll, collatSym: collatSym.toUpperCase() };
}

async function renderHeader(cfg: any) {
  const b = await getBalancesInline(cfg).catch(() => ({ sol: NaN, wsol: NaN, collat: NaN, collatSym: "" }));
  const solTxt = isNaN(b.sol) ? "?" : b.sol.toFixed(4);
  const wsolTxt = isNaN(b.wsol) ? "?" : b.wsol.toFixed(4);
  const collTxt = isNaN(b.collat) ? "?" : b.collat.toFixed(4);

  console.log("╔══════════════════════════════════════════════════════════════╗");
  console.log("║  🧭  Jupiter Perps Console                                   ║");
  console.log("║      rpc: ", String(cfg.rpc ?? "").padEnd(47, " "), "║");
  console.log("║      kp : ", String(cfg.kp ?? "").padEnd(47, " "), "║");
  console.log("║      pos: ", shortId(String(cfg.position ?? "")).padEnd(47, " "), "║");
  console.log(
    "║      col: ",
    (cfg.collatMint ? shortId(String(cfg.collatMint)) : "WSOL(default)").padEnd(47, " "),
    "║"
  );
  const balLine = `sol:${solTxt} | wsol:${wsolTxt} | ${b.collatSym}:${collTxt}`;
  console.log(
    "║      bal: ",
    balLine
      .replace(`sol:${solTxt}`, `sol:${color(b.sol, solTxt)}`)
      .replace(`wsol:${wsolTxt}`, `wsol:${color(b.wsol, wsolTxt)}`)
      .replace(`${b.collatSym}:${collTxt}`, `${b.collatSym}:${color(b.collat, collTxt)}`)
      .padEnd(47, " "),
    "║"
  );
  console.log("╠══════════════════════════════════════════════════════════════╣");
}
function is429(s: string) { return /Too Many Requests| code\":\s*429/i.test(s); }
function nextRpc(cfg: any) {
  if (!Array.isArray(cfg.rpcList) || cfg.rpcList.length === 0) return cfg.rpc;
  cfg.rpcIndex = ((cfg.rpcIndex || 0) + 1) % cfg.rpcList.length;
  cfg.rpc = cfg.rpcList[cfg.rpcIndex];
  return cfg.rpc;
}
function sleep(ms: number) { return new Promise((resolve) => setTimeout(resolve, ms)); }

function runCapture(label: string, scriptAbsPath: string, args: string[]) {
  const res = spawnSync("npx", ["--yes", "tsx", scriptAbsPath, ...args], { shell: true, encoding: "utf8" });
  const stdout = (res.stdout || "").toString();
  const stderr = (res.stderr || "").toString();
  const combined = stdout + "\n" + stderr;
  const status = res.status ?? 1;
  return { status, stdout, stderr, combined };
}

function printFailureTail(combined: string, tail = 60) {
  const lines = combined.split(/\r?\n/).filter(Boolean);
  const last = lines.slice(-tail);
  console.log("\n❌ Open failed. Tail of logs:");
  for (const l of last) console.log("   ", l);
}

/**
 * Robustly parse Anchor ConstraintSeeds from noisy logs.
 * Handles:
 *  - lines wrapped in quotes and ending with commas
 *  - "Program log:" prefixes
 *  - Left/Right on same line OR next line
 */
function findRightFromLogs(
  combined: string
): { which?: "position" | "position_request"; left?: string; right?: string } | null {
  const lines = combined
    .split(/\r?\n/)
    .map((l) => l.trim().replace(/^['"]|['"],?$/g, "")); // strip quotes/commas

  const b58 = /([1-9A-HJ-NP-Za-km-z]{32,44})/;
  for (let i = 0; i < lines.length; i++) {
    const L = lines[i];

    // Look for the anchor error line with which account failed
    if (!/ConstraintSeeds/i.test(L)) continue;

    let which: "position" | "position_request" | undefined;
    const mWhich = L.match(/account:\s*([A-Za-z_]+)/i);
    if (mWhich) {
      const name = mWhich[1].toLowerCase();
      if (name.includes("position_request")) which = "position_request";
      else if (name === "position") which = "position";
    }

    // Scan the next ~10 lines to find Left/Right + pubkeys
    let left: string | undefined, right: string | undefined;
    for (let j = i + 1; j < Math.min(lines.length, i + 12); j++) {
      const s = lines[j];

      if (/Left:/i.test(s)) {
        // pubkey could be on this line or the next
        left = (s.match(b58)?.[1]) || (lines[j + 1]?.match(b58)?.[1]);
      }
      if (/Right:/i.test(s)) {
        right = (s.match(b58)?.[1]) || (lines[j + 1]?.match(b58)?.[1]);
      }
      if (left && right) break;
    }

    if (right) return { which, left, right };
  }
  return null;
}

// Build args for perps_open_market.ts with optional PDA overrides.
function buildOpenArgs(cfg: any, overrides?: { position?: string; positionRequest?: string }, dryRun = false) {
  const args = [
    "--rpc", cfg.rpc,
    "--kp", cfg.kp,
    "--market", cfg.market,
    "--side", cfg.side,
    "--size-usd", String(cfg.sizeUsd),
    "--collat", String(cfg.collat),
    "--position", overrides?.position ?? cfg.position,
    "--position-request", overrides?.positionRequest ?? cfg.positionRequest,
    "--cu-limit", String(cfg.cuLimit),
    "--priority-microlamports", String(cfg.priorityMicrolamports),
  ];
  if (cfg.collatMint) args.push("--collat-mint", String(cfg.collatMint));
  if (cfg.oraclePrice != null && cfg.slip != null) {
    args.push("--oracle-price", String(cfg.oraclePrice), "--slip", String(cfg.slip));
  } else if (cfg.maxPrice != null) {
    args.push("--max-price", String(cfg.maxPrice));
  } else if (cfg.minPrice != null) {
    args.push("--min-price", String(cfg.minPrice));
  }
  if (dryRun) args.push("--dry-run");
  return args;
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

  for (let attempt = 1; attempt <= 3; attempt++) {
    if (attempt > 1) {
      console.log("\n⏳ backoff…");
      await new Promise((r) => setTimeout(r, 800 + Math.random() * 1200));
    }

    console.log(`\n──────────────────── Open Perp (attempt ${attempt}) ────────────────────`);
    const res = await runTee("Open", SCRIPTS.open, buildOpenArgs(cfg));

    if (res.status === 0) {
      console.log("\n⏱️  Watching position for fill… (Ctrl+C to stop)");
      const t0 = Date.now();
      const poll = Number(cfg.pollMs) || 6000;
      const deadline = Date.now() + Number(cfg.timeoutS || 240) * 1000;
      while (true) {
        const r = spawnSync(
          "npx",
          ["--yes", "tsx", SCRIPTS.readAcct, "--rpc", cfg.rpc, "--id", cfg.position, "--kind", "position"],
          { shell: true, encoding: "utf8" }
        );
        const m = (r.stdout || "").toString().match(/sizeUsd:\s*'(\d+)'/);
        if (m) {
          const sz = Number(m[1]);
          console.log(`🔎 sizeUsd=${sz}  elapsed=${Math.floor((Date.now() - t0) / 1000)}s`);
          if (sz > 0) {
            console.log("✅ filled");
          }
        }
        if (Date.now() > deadline || (m && Number(m[1]) > 0)) break;
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, poll);
      }
      return;
    }

    printFailureTail(res.combined, 60);
  }

  console.log("\n❌ Open failed after attempts. See logs above.");
}


async function actionDryRunSim(cfg: any) {
  console.log("🧪 Dry-run Simulate");

  const openArgs = buildOpenArgs(cfg, undefined, true);
  console.log(`\n──────────────────── Simulate Open ────────────────────`);
  const res = runCapture("Simulate Open", SCRIPTS.open, openArgs);

  if (res.status !== 0) {
    printFailureTail(res.combined, 60);
    console.log(`\n❌ Dry-run failed. See logs above.`);
    return;
  }

  console.log(`\n✅ Dry-run succeeded.`);
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
  await edit("collatMint");
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
    await renderHeader(cfg);
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
