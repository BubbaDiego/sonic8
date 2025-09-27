/* Open/Increase position at market, with optional collateral deposit */
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import { performance } from "perf_hooks";
import {
  AnchorProvider,
  Program,
  Wallet,
  setProvider,
  type Idl,
} from "@coral-xyz/anchor";
import * as web3 from "@solana/web3.js";
import {
  PublicKey,
  SystemProgram,
  Keypair,
  VersionedTransaction,
  TransactionMessage,
  ComputeBudgetProgram,
} from "@solana/web3.js";
import {
  getAssociatedTokenAddressSync,
  createAssociatedTokenAccountIdempotentInstruction,
  TOKEN_PROGRAM_ID,
  ASSOCIATED_TOKEN_PROGRAM_ID,
} from "@solana/spl-token";
import { RpcPool } from "../lib/rpc_failover.js";
import { bar, info, kv, ok, fail } from "../utils/logger.js";
import * as cfg from "../config/perps.js";
import {
  toMicroUsd,
  toTokenAmount,
  sideToEnum,
} from "../utils/resolve.js";
import { IDL as JUP_PERPS_IDL } from "../idl/jupiter-perpetuals-idl.js";
import { toPk } from "../utils/pk.js";
import {
  createAtaIxStrict,
  deriveAtaStrict,
  detectTokenProgramForMint,
} from "../utils/ata.js";

type StepKey =
  | "cli"
  | "rpc"
  | "idl"
  | "perps"
  | "pool"
  | "custodies"
  | "pdas"
  | "positionSelect"
  | "ataOwner"
  | "ataRequest"
  | "ataPosition"
  | "accountsBuilt"
  | "simulate"
  | "submit"
  | "programPass"
  | "watch";

type ValidationSubStepKey =
  | "vSeeds"
  | "vRequestSeeds"
  | "vCustodyOrder"
  | "vCollateralAccount";

const SUBSTEP_LABEL: Record<ValidationSubStepKey, string> = {
  vSeeds: "Position PDA (seeds)",
  vRequestSeeds: "PositionRequest PDA (seeds)",
  vCustodyOrder: "Custody order", // market vs collateral
  vCollateralAccount: "Collateral token account",
};

const STEP_LABEL: Record<StepKey, string> = {
  cli: "Parse CLI + config",
  rpc: "RPC connect & provider",
  idl: "IDL loaded & program",
  perps: "Fetch Perpetuals (singleton)",
  pool: "Fetch Pool (singleton)",
  custodies: "Load custodies & map mints",
  pdas: "Resolve PDAs",
  positionSelect: "Select position PDA for order",
  ataOwner: "ATA: Owner USDC",
  ataRequest: "ATA: PositionRequest USDC",
  ataPosition: "ATA: Position USDC",
  accountsBuilt: "Build accountsStrict",
  simulate: "Simulate / Dry-run",
  submit: "Submit transaction",
  programPass: "Program validations pass",
  watch: "Watch/stream position",
};

const STEP_ORDER: StepKey[] = [
  "cli",
  "rpc",
  "idl",
  "perps",
  "pool",
  "custodies",
  "pdas",
  "positionSelect",
  "ataOwner",
  "ataRequest",
  "ataPosition",
  "accountsBuilt",
  "simulate",
  "submit",
  "programPass",
  "watch",
];

class StepTracker {
  private runStart = performance.now();
  private data = new Map<
    StepKey,
    { ok?: boolean; note?: string; t0?: number; t1?: number }
  >();
  private subData = new Map<
    StepKey,
    Map<
      ValidationSubStepKey,
      { ok?: boolean; note?: string; t0?: number; t1?: number }
    >
  >();
  private printed = false;

  start(key: StepKey, note?: string) {
    const now = performance.now();
    const prev = this.data.get(key) || {};
    this.data.set(key, { ...prev, t0: prev.t0 ?? now, note: note ?? prev.note });
  }

  ok(key: StepKey, note?: string) {
    this.end(key, true, note);
  }

  fail(key: StepKey, note?: string) {
    this.end(key, false, note);
  }

  async time<T>(key: StepKey, fn: () => Promise<T>, note?: string): Promise<T> {
    this.start(key, note);
    try {
      const out = await fn();
      this.ok(key, note);
      return out;
    } catch (e) {
      this.fail(key, note);
      throw e;
    }
  }

  get(key: StepKey) {
    return this.data.get(key);
  }

  subStart(key: ValidationSubStepKey, note?: string) {
    this.subSet("programPass", key, { note, ok: undefined }, false);
  }

  subOk(key: ValidationSubStepKey, note?: string) {
    this.subSet("programPass", key, { ok: true, note }, true);
  }

  subFail(key: ValidationSubStepKey, note?: string) {
    this.subSet("programPass", key, { ok: false, note }, true);
  }

  hasSub(key: ValidationSubStepKey) {
    return this.subData.get("programPass")?.has(key) ?? false;
  }

  getSub(key: ValidationSubStepKey) {
    return this.subData.get("programPass")?.get(key);
  }

  private subSet(
    parent: StepKey,
    key: ValidationSubStepKey,
    val: { ok?: boolean; note?: string },
    end: boolean,
  ) {
    const now = performance.now();
    const forParent = this.subData.get(parent) ?? new Map();
    const prev = forParent.get(key) ?? { t0: now };
    const next = {
      ...prev,
      ...val,
      t0: prev.t0 ?? now,
      t1: end ? now : prev.t1,
    };
    forParent.set(key, next);
    this.subData.set(parent, forParent);
  }

  private end(key: StepKey, ok: boolean, note?: string) {
    const now = performance.now();
    const prev = this.data.get(key) || {};
    const t0 = prev.t0 ?? this.runStart;
    this.data.set(key, { ok, note: note ?? prev.note, t0, t1: now });
  }

  print(title = "Order Placement Checklist") {
    const fmt = (ms?: number) => {
      if (ms == null) return "";
      if (ms < 1) return ` — ${ms.toFixed(2)}ms`;
      if (ms < 1000) return ` — ${ms.toFixed(0)}ms`;
      return ` — ${(ms / 1000).toFixed(2)}s`;
    };
    console.log(`\n──────── ${title} ────────`);
    STEP_ORDER.forEach((k, i) => {
      const row = this.data.get(k);
      const icon = row?.ok === true ? "✅" : row?.ok === false ? "💀" : "•";
      const name = STEP_LABEL[k];
      const note = row?.note ? ` — ${row.note}` : "";
      const dur =
        row?.t0 != null && row?.t1 != null ? fmt(row.t1 - row.t0) : "";
      const idx = String(i + 1).padStart(2, "0");
      console.log(`${idx}) ${icon}  ${name}${note}${dur}`);

      const substeps = this.subData.get(k);
      if (substeps && substeps.size) {
        const entries = Array.from(substeps.entries()).sort(([a], [b]) =>
          a.localeCompare(b),
        );
        entries.forEach(([subKey, subRow], subIdx) => {
          const subIcon = subRow.ok === true ? "✅" : subRow.ok === false ? "💀" : "•";
          const label = SUBSTEP_LABEL[subKey];
          const subNote = subRow.note ? ` — ${subRow.note}` : "";
          const subDur =
            subRow.t0 != null && subRow.t1 != null ? fmt(subRow.t1 - subRow.t0) : "";
          const letter = String.fromCharCode("a".charCodeAt(0) + subIdx);
          console.log(`    ${idx}.${letter}) ${subIcon}  ${label}${subNote}${subDur}`);
        });
      }
    });
    console.log("────────────────────────────────────────\n");
    this.printed = true;
  }

  hasPrinted() {
    return this.printed;
  }
}

let __finalChecklistHookInstalled = false;
function installFinalChecklistPrint(
  steps: StepTracker,
  finalTitle = "Order Placement Checklist (Final)",
) {
  if (__finalChecklistHookInstalled) return;
  __finalChecklistHookInstalled = true;
  const finalPrint = () => {
    try {
      steps.print(finalTitle);
    } catch {}
  };
  process.once("exit", finalPrint);
  process.once("beforeExit", finalPrint);
  process.once("uncaughtException", (err) => {
    finalPrint();
    console.error(err);
    process.exit(1);
  });
  process.once("unhandledRejection", (r: any) => {
    finalPrint();
    console.error(r);
    process.exit(1);
  });
}

async function makeProviderAndProgram(
  conn: web3.Connection,
  wallet: Wallet,
  idl: Idl,
  programId: web3.PublicKey,
) {
  const provider = new AnchorProvider(conn, wallet, {
    commitment: "confirmed",
  });
  setProvider(provider);
  const program = new Program(idl, programId, provider);
  return { provider, program };
}

type CustodyInfo = {
  pubkey: web3.PublicKey;
  account: any;
  mint: web3.PublicKey;
};

function pickCustodyByMint(custodies: CustodyInfo[], mint: web3.PublicKey) {
  const c = custodies.find((x) => x.mint.equals(mint));
  if (!c) throw new Error(`No custody found for mint ${mint.toBase58()}`);
  return c.pubkey;
}

function collectAllLogLines(err: any): string[] {
  const a: string[] = Array.isArray(err?.transactionLogs) ? err.transactionLogs : [];
  const b: string[] = Array.isArray(err?.logs) ? err.logs : [];
  const c: string[] = Array.isArray(err?.errorLogs) ? err.errorLogs : [];
  return [...a, ...b, ...c].filter((x) => typeof x === "string");
}

function extractRightAddress(logs: string[]): string | null {
  const base58 = /[1-9A-HJ-NP-Za-km-z]{32,44}/;
  const window = logs.filter((l) => l.includes("Right"));
  for (const line of window) {
    const match = line.match(base58);
    if (match?.[0]) return match[0];
  }
  return null;
}

function markValidationsFromLogs(steps: StepTracker, logs: string[]) {
  if (!logs.length) return;
  const hasPositionSeeds = logs.some(
    (l) => l.includes("ConstraintSeeds") && l.includes("account: position"),
  );
  const hasRequestSeeds = logs.some(
    (l) => l.includes("ConstraintSeeds") && l.includes("account: positionRequest"),
  );
  const hasInvalidCollateral = logs.some((l) => l.includes("Invalid collateral account"));
  const hasInvalidToken = logs.some((l) => l.includes("Invalid token account"));

  if (hasPositionSeeds) {
    steps.subFail("vSeeds", "position PDA mismatch");
  }
  if (hasRequestSeeds) {
    steps.subFail("vRequestSeeds", "positionRequest PDA mismatch");
  }
  if (hasInvalidCollateral) {
    steps.subFail("vCustodyOrder", "custody order mismatch");
  }
  if (hasInvalidToken) {
    steps.subFail("vCollateralAccount", "collateral account invalid");
  }
}

async function debugPrintIx(program: Program, m: any, label: string) {
  const ix = await m.instruction();
  const idlIx = program.idl.instructions.find(
    (i: any) => i.name === "createIncreasePositionMarketRequest",
  );
  console.log(`🔎 Final ix accounts (${label}) (IDL name → pubkey):`);
  ix.keys.forEach((k: web3.AccountMeta, i: number) => {
    const name = idlIx?.accounts?.[i]?.name ?? `idx_${i}`;
    console.log(`${String(i).padStart(2)} ${name} → ${k.pubkey.toBase58()}`);
  });
  return ix;
}

function makePositionUsdcAtaIx(
  payer: web3.PublicKey,
  positionPk: web3.PublicKey,
  usdcMint: web3.PublicKey,
) {
  const ata = getAssociatedTokenAddressSync(usdcMint, positionPk, true);
  const ix = createAssociatedTokenAccountIdempotentInstruction(payer, ata, positionPk, usdcMint);
  return { ata, ix };
}

// Helpers to derive PDAs from the Anchor IDL seeds
function seedToBytes(
  seed: any,
  ctx: Record<string, PublicKey | string | Buffer>,
  programId: PublicKey,
): Buffer {
  const kind = seed?.kind ?? seed?.type;
  if (!kind) throw new Error("IDL seed missing kind/type");

  const asPkBuf = (v: any) =>
    v instanceof PublicKey ? v.toBuffer() : new PublicKey(v).toBuffer();

  switch (kind) {
    case "const":
      if (typeof seed.value === "string") return Buffer.from(seed.value);
      if (typeof seed.value === "number") {
        const b = Buffer.alloc(8);
        b.writeUInt32LE(seed.value, 0);
        return b;
      }
      throw new Error(`Unhandled const seed value: ${JSON.stringify(seed)}`);

    case "program":
      return programId.toBuffer();

    case "account": {
      const path = seed.path || seed.account || seed.name;
      if (!path || !ctx[path]) throw new Error(`Missing account seed path '${path}'`);
      return asPkBuf(ctx[path]);
    }

    case "arg": {
      const name = seed.path || seed.name;
      throw new Error(`IDL seed uses arg '${name}', not supported in this callsite`);
    }

    default:
      throw new Error(`Unknown seed kind: ${kind}`);
  }
}

function getIdlAccountPdaSeeds(program: any, accountName: string): any[] | null {
  const idl = program?.idl;
  if (!idl) return null;
  const acc = (idl.accounts || []).find(
    (a: any) => (a.name || "").toLowerCase() === accountName.toLowerCase(),
  );
  const seeds = acc?.pda?.seeds || acc?.seeds;
  return Array.isArray(seeds) ? seeds : null;
}

function derivePdaByIdl(
  program: any,
  accountName: string,
  ctx: Record<string, PublicKey | string | Buffer>,
): PublicKey | null {
  const seeds = getIdlAccountPdaSeeds(program, accountName);
  if (!seeds) return null;
  const seedBytes = seeds.map((s: any) => seedToBytes(s, ctx, program.programId));
  const [pda] = PublicKey.findProgramAddressSync(seedBytes, program.programId);
  return pda;
}

function derivePositionFallback(
  programId: PublicKey,
  pool: PublicKey,
  owner: PublicKey,
  marketCustody: PublicKey,
  collateralCustody: PublicKey,
): PublicKey {
  const seeds = [
    Buffer.from("position"),
    pool.toBuffer(),
    owner.toBuffer(),
    marketCustody.toBuffer(),
    collateralCustody.toBuffer(),
  ];
  return PublicKey.findProgramAddressSync(seeds, programId)[0];
}

function derivePositionRequestFallback(
  programId: PublicKey,
  pool: PublicKey,
  owner: PublicKey,
  marketCustody: PublicKey,
  collateralCustody: PublicKey,
): PublicKey {
  const seeds = [
    Buffer.from("position_request"),
    pool.toBuffer(),
    owner.toBuffer(),
    marketCustody.toBuffer(),
    collateralCustody.toBuffer(),
  ];
  return PublicKey.findProgramAddressSync(seeds, programId)[0];
}

type PdaInputs = {
  pool: PublicKey;
  owner: PublicKey;
  marketCustody: PublicKey;
  collateralCustody: PublicKey;
};

function derivePdaByl(program: any, acc: string, ctx: any) {
  return derivePdaByIdl(program, acc, ctx);
}

function derivePositionDeterministic(program: any, inp: PdaInputs): PublicKey {
  const ctx = {
    pool: inp.pool,
    owner: inp.owner,
    custody: inp.marketCustody,
    marketCustody: inp.marketCustody,
    collateralCustody: inp.collateralCustody,
  };
  const byIdl = derivePdaByl(program, "position", ctx);
  return (
    byIdl ??
    derivePositionFallback(
      program.programId,
      inp.pool,
      inp.owner,
      inp.marketCustody,
      inp.collateralCustody,
    )
  );
}

function derivePositionRequestDeterministic(
  program: any,
  inp: PdaInputs,
  position: PublicKey,
): PublicKey {
  const ctx = {
    pool: inp.pool,
    owner: inp.owner,
    position,
    custody: inp.marketCustody,
    marketCustody: inp.marketCustody,
    collateralCustody: inp.collateralCustody,
  };
  const byIdl =
    derivePdaByl(program, "positionRequest", ctx) ||
    derivePdaByl(program, "position_request", ctx);
  return (
    byIdl ??
    derivePositionRequestFallback(
      program.programId,
      inp.pool,
      inp.owner,
      inp.marketCustody,
      inp.collateralCustody,
    )
  );
}

// Build accounts with selectable mapping mode
async function sendIncreasePositionRobust(
  params: {
  program: Program;
  preIxs: web3.TransactionInstruction[];
  postIxs: web3.TransactionInstruction[];
  ixArgs: any;

  payer: web3.PublicKey;
  marketCustodyPk: web3.PublicKey;
  collateralCustodyPk: web3.PublicKey;
  collateralMintPk: web3.PublicKey;
  derived: { position: web3.PublicKey; positionRequest: web3.PublicKey };
  orderMode: "idl" | "swapped";
  buildAccountsStrictBase: () => any;
},
  steps: StepTracker,
) {
  const {
    program,
    ixArgs,
    payer,
    collateralMintPk,
    marketCustodyPk,
    collateralCustodyPk,
    derived,
    orderMode,
    buildAccountsStrictBase,
  } = params;

  const preIxsBase = [...params.preIxs];
  const postIxs = [...params.postIxs];

  function rebuildPreIxs(note?: string) {
    steps.start("ataPosition");
    const { ix: posAtaIx } = makePositionUsdcAtaIx(
      payer,
      derived.position,
      collateralMintPk,
    );
    const rebuilt = [...preIxsBase, posAtaIx];
    steps.ok("ataPosition", note ?? `ensured for ${derived.position.toBase58()}`);
    return rebuilt;
  }

  const preIxs = rebuildPreIxs();

  const buildAccounts = () => {
    const base = buildAccountsStrictBase();
    if (orderMode === "swapped") {
      return {
        ...base,
        custody: collateralCustodyPk,
        collateralCustody: marketCustodyPk,
      };
    }
    return base;
  };

  async function trySend(label: string) {
    console.log(
      "➡️ using position for send:",
      derived.position.toBase58(),
      "| order:",
      orderMode,
    );
    steps.start("accountsBuilt");
    const accounts = buildAccounts();
    steps.ok("accountsBuilt", `Using ${orderMode} order for ${shortId(derived.position.toBase58())}`);
    const m = program.methods
      .createIncreasePositionMarketRequest(ixArgs)
      .accountsStrict(accounts)
      .preInstructions(preIxs)
      .postInstructions(postIxs);
    await debugPrintIx(program, m, label);
    steps.start("submit");
    await m.rpc();
    steps.ok("submit");
  }

  for (let attempt = 1; attempt <= 4; attempt++) {
    try {
      await trySend(`attempt ${attempt}/4`);
      steps.ok("programPass");
      (Object.keys(SUBSTEP_LABEL) as ValidationSubStepKey[]).forEach((key) => {
        const status = steps.getSub(key);
        if (!status || status.ok == null) {
          steps.subOk(key, "passed");
        }
      });
      steps.ok("watch");
      return derived.position;
    } catch (e: any) {
      if (!steps.get("submit")?.ok) {
        steps.ok("submit");
      }
      const logs = collectAllLogLines(e);
      const code = e?.error?.errorCode?.number ?? e?.errorCode?.number ?? null;

      if (code === 2006) {
        const right = extractRightAddress(logs);
        const note = right
          ? `Program expects position=${right} (derived=${derived.position.toBase58()})`
          : "Seeds mismatch";
        markValidationsFromLogs(steps, logs);
        steps.fail("programPass", note);
        throw e;
      }

      markValidationsFromLogs(steps, logs);

      if (logs.some((l) => l.includes("Invalid collateral account"))) {
        steps.subFail("vCustodyOrder", "swap custody order not allowed under deterministic mode");
        steps.fail("programPass", "custody order mismatch");
        throw e;
      }

      throw e;
    }
  }

  steps.fail("programPass", "Retries exhausted");
  throw new Error("sendIncreasePositionRobust: retries exhausted");
}

function shortId(s: string) {
  return s.length > 10 ? `${s.slice(0, 4)}…${s.slice(-4)}` : s;
}
function labelFor(programId: string) {
  return programId === "ComputeBudget111111111111111111111111111111"
    ? "ComputeBudget"
    : programId === "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
      ? "AssociatedToken"
      : programId === "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        ? "Token"
        : programId === "11111111111111111111111111111111"
          ? "System"
          : programId === "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu"
            ? "Perps"
            : shortId(programId);
}
function formatLogs(raw: string[]): string[] {
  // squash repetitive AToken “CreateIdempotent” chatter and Token size/init chatter
  const skip = [
    "Instruction: GetAccountDataSize",
    "return: TokenkegQfe",
    "Please upgrade to SPL Token 2022 for immutable owner support",
    "Instruction: InitializeAccount3",
  ];
  const out: string[] = [];
  for (const l of raw || []) {
    if (skip.some((k) => l.includes(k))) continue;
    // Prefix with a label if the line starts with “Program <pid>” or “Program log: …”
    const m = l.match(/^Program\s+([A-Za-z0-9]+)\s.*|^Program log:\s(.*)$/);
    if (m) {
      // keep as-is but compact the pid into a label when present
      const pid = l.match(/^Program\s+([A-Za-z0-9]+)/)?.[1] ?? "";
      if (pid)
        out.push(
          `• ${labelFor(pid)} → ${l.replace(/^Program\s+[A-Za-z0-9]+\s/, "")}`,
        );
      else out.push(`• ${l.replace(/^Program log:\s/, "")}`);
    } else {
      out.push(l);
    }
  }
  // collapse duplicate consecutive lines
  return out.filter((v, i, a) => i === 0 || v !== a[i - 1]);
}

(async () => {
  const steps = new StepTracker();
  installFinalChecklistPrint(steps);
  steps.start("cli");
  try {
    const argv = await yargs(hideBin(process.argv))
      .option("rpc", { type: "string", demandOption: true })
      .option("kp", {
        type: "string",
        demandOption: true,
        describe: "Path to keypair JSON/base58",
    })
    .option("rpc-fallbacks", {
      type: "string",
      describe: "Comma-separated fallback RPC endpoints",
    })
    .option("market", {
      type: "string",
      choices: ["SOL", "ETH", "BTC"] as const,
      demandOption: true,
    })
    .option("side", {
      type: "string",
      choices: ["long", "short"] as const,
      demandOption: true,
    })
    .option("size-usd", {
      type: "number",
      demandOption: true,
      describe: "USD notional for size",
    })
    .option("collat", {
      type: "number",
      default: 0,
      describe: "Collateral token amount (UI units)",
    })
    .option("collat-mint", {
      type: "string",
      describe:
        "Override collateral mint (default: WSOL for long, USDC for short)",
    })
    .option("oracle-price", {
      type: "number",
      describe: "Oracle/mark price in USD for guardrail calc",
    })
    .option("slip", {
      type: "number",
      describe: "Slippage fraction for guardrail (e.g., 0.02)",
    })
    .option("max-price", {
      type: "number",
      describe: "Explicit max price (LONG)",
    })
    .option("min-price", {
      type: "number",
      describe: "Explicit min price (SHORT)",
    })
    .option("dry-run", { type: "boolean", default: false })
    .option("flip-custody-order", {
      type: "boolean",
      default: false,
      describe: "Force custody↔collateralCustody order swap (diagnostics)",
    })
    .option("cu-limit", {
      type: "number",
      default: 800_000,
      describe: "Compute unit limit to request for the transaction",
    })
    .option("priority-microlamports", {
      type: "number",
      default: 100_000,
      describe: "Micro-lamports to pay per compute unit for priority fees",
    })
    .strict()
    .parse();
    steps.ok("cli");

  const rpc = argv.rpc as string;
  const rpcFallbacksCsv =
    (argv["rpc-fallbacks"] as string | undefined) ??
    process.env.SONIC_SOLANA_RPC_FALLBACKS ??
    "";

  const rpcPool = new RpcPool(rpc, rpcFallbacksCsv, {
    perEndpointMaxRetries: 5,
    baseDelayMs: 500,
    maxDelayMs: 15000,
  });

  const idl = JUP_PERPS_IDL as Idl;
  const meta = (idl as any)?.metadata;
  const programId = new PublicKey(
    meta?.address ??
      (() => {
        throw new Error("IDL.metadata.address missing; update IDL");
      })(),
  );

  const kp = cfg.loadKeypair(argv.kp);
  const wallet = new Wallet(kp);

  const endpointFor = (conn: web3.Connection) =>
    (conn as any).rpcEndpoint ??
    (conn as any)._rpcEndpoint ??
    rpcPool.currentEndpoint();

  let provider!: AnchorProvider;
  let program!: Program<any>;
  let currentEndpoint = "";
  const owner = wallet.payer as Keypair;

  async function ensureProviderOnConnection(conn: web3.Connection) {
    const endpoint = endpointFor(conn);
    if (!provider || currentEndpoint !== endpoint) {
      const built = await steps.time(
        "rpc",
        async () =>
          steps.time(
            "idl",
            async () => makeProviderAndProgram(conn, wallet, idl, programId),
            programId.toBase58(),
          ),
        endpoint,
      );
      provider = built.provider;
      program = built.program as Program<any>;
      currentEndpoint = endpoint;
      steps.ok("idl", `Program ${program.programId.toBase58()}`);
    }
  }

  bar("Bootstrap", "🔗");

  let perpetuals!: { publicKey: PublicKey; account: any };
  let pool!: { publicKey: PublicKey; account: any };
  let allCustodies: CustodyInfo[] = [];
  let bootstrapLogged = false;

  await rpcPool.runWithFailover(async (conn) => {
    await ensureProviderOnConnection(conn);
    const endpoint = endpointFor(conn);
    if (!bootstrapLogged) {
      info("🧭", `Network: ${endpoint}`);
      kv("Owner", wallet.publicKey.toBase58());
      kv("Program", programId.toBase58());
      ok("IDL loaded and program ready");
      bootstrapLogged = true;
    }

    perpetuals = await steps.time(
      "perps",
      async () => cfg.getSingletonPerpetuals(program),
    );
    steps.ok("perps", perpetuals.publicKey.toBase58());
    pool = await steps.time("pool", async () => cfg.getSingletonPool(program));
    steps.ok("pool", pool.publicKey.toBase58());
    const allCustodiesRaw = await steps.time(
      "custodies",
      async () => cfg.getCustodies(program, pool.account),
    );
    allCustodies = allCustodiesRaw.map((c) => ({
      ...c,
      mint: new PublicKey(c.account.mint as PublicKey),
    }));
    steps.ok("custodies", `${allCustodies.length} loaded`);
    return true;
  }, "bootstrap/perps+pool+custodies");

  const ix = program.idl?.instructions?.find(
    (i: any) => i.name === "createIncreasePositionMarketRequest",
  );
  console.log(
    "IDL accounts:",
    ix?.accounts.map((a: any) => a.name),
  );

  const marketMint = (cfg.MINTS as any)[argv.market] as PublicKey;
  const sideEnum = sideToEnum(argv.side);
  const flipCustodyOrder = argv["flip-custody-order"] === true;

  const marketCustodyPk = pickCustodyByMint(allCustodies, marketMint);
  const defaultCollat = argv.side === "long" ? marketMint : cfg.MINTS.USDC;
  const collatMintArg = (argv["collat-mint"] as unknown) ?? null;
  const collateralMint = collatMintArg
    ? toPk("collat-mint", collatMintArg)
    : defaultCollat;
  let collateralCustodyPk = pickCustodyByMint(allCustodies, collateralMint);
  let collateralCustodyInfo = allCustodies.find((c) =>
    c.pubkey.equals(collateralCustodyPk),
  );
  if (!collateralCustodyInfo)
    throw new Error("Unable to resolve collateral custody info");
  console.log(
    "🔑  Mints :: marketMint=",
    (marketMint as any).toBase58?.() ?? String(marketMint),
    " collateralMint=",
    (collateralMint as any).toBase58?.() ?? String(collateralMint),
  );
  console.log("🧪 custody (market):     ", marketCustodyPk.toBase58());
  console.log("🧪 collateralCustody:  ", collateralCustodyPk.toBase58());
  console.log("🧪 inputMint:          ", collateralMint.toBase58());

  bar("PDAs", "🧩");
  const pdaInputs: PdaInputs = {
    pool: pool.publicKey,
    owner: wallet.publicKey,
    marketCustody: marketCustodyPk,
    collateralCustody: collateralCustodyPk,
  };
  const DERIVED = await steps.time(
    "pdas",
    async () => {
      const position = derivePositionDeterministic(program, pdaInputs);
      const positionRequest = derivePositionRequestDeterministic(
        program,
        pdaInputs,
        position,
      );
      return { position, positionRequest };
    },
    "Deriving deterministic PDAs",
  );
  (Object.keys(SUBSTEP_LABEL) as ValidationSubStepKey[]).forEach((key) => {
    if (!steps.hasSub(key)) {
      steps.subStart(key);
    }
  });
  steps.ok("pdas", shortId(DERIVED.position.toBase58()));
  kv("Position", DERIVED.position.toBase58());
  kv("PosRequest", DERIVED.positionRequest.toBase58());
  const positionPk = DERIVED.position;
  const positionRequest = DERIVED.positionRequest;
  const havePR = false;

  const decimals = (collateralCustodyInfo.account.decimals as number) ?? 9;
  // Discovery run = no token transfer → set collat=0 on the wire when !havePR
  const sizeUsdDeltaDisc = toMicroUsd(argv["size-usd"]);
  const collateralTokenDelta = havePR
    ? toTokenAmount(argv.collat, decimals)
    : new cfg.BN(0); // discovery → 0 on-chain

  // Step 2 — Funding (owner ATA) & escrow ATAs (position request + position)
  const usdcMint = new PublicKey(
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  );
  const wsolMint = new PublicKey("So11111111111111111111111111111111111111112");

  const usdcProgramId = await detectTokenProgramForMint(
    provider.connection,
    usdcMint,
  );
  const wsolProgramId = await detectTokenProgramForMint(
    provider.connection,
    wsolMint,
  );

  const tokenProgramCache = new Map<string, PublicKey>();
  tokenProgramCache.set(usdcMint.toBase58(), usdcProgramId);
  tokenProgramCache.set(wsolMint.toBase58(), wsolProgramId);

  const mintLabel = (mint: PublicKey) => {
    if (mint.equals(usdcMint)) return "USDC";
    if (mint.equals(wsolMint)) return "WSOL";
    return mint.toBase58();
  };

  const getTokenProgramIdForMint = async (mint: PublicKey) => {
    const key = mint.toBase58();
    const cached = tokenProgramCache.get(key);
    if (cached) return cached;
    const detected = await detectTokenProgramForMint(provider.connection, mint);
    const resolved = detected ?? TOKEN_PROGRAM_ID;
    tokenProgramCache.set(key, resolved);
    return resolved;
  };

  let ownerTokenProgramId!: PublicKey;
  let ownerAtaInit!: ReturnType<typeof createAtaIxStrict>;
  await steps.time("ataOwner", async () => {
    ownerTokenProgramId = await getTokenProgramIdForMint(collateralMint);
    ownerAtaInit = createAtaIxStrict(
      wallet.publicKey,
      collateralMint,
      wallet.publicKey,
      /*allowOwnerOffCurve=*/ false,
      ownerTokenProgramId,
    );
    console.log(`🧪 ATA debug (${mintLabel(collateralMint)}, wallet):`, {
      mint: shortId(collateralMint.toBase58()),
      owner: shortId(wallet.publicKey.toBase58()),
      allowOwnerOffCurve: false,
      tokenProgramId: shortId(ownerTokenProgramId.toBase58()),
      ata: shortId(ownerAtaInit.ata.toBase58()),
    });
    const expectedOwnerAta = deriveAtaStrict(
      collateralMint,
      wallet.publicKey,
      false,
      ownerTokenProgramId,
    );
    if (!ownerAtaInit.ata.equals(expectedOwnerAta)) {
      throw new Error("ATA mismatch (wallet) vs seed derivation");
    }
  });
  steps.ok("ataOwner", shortId(ownerAtaInit.ata.toBase58()));

  // Step 3 — Amounts & guardrail
  let priceGuard: cfg.BN | null = null;
  if (
    typeof argv["oracle-price"] === "number" &&
    typeof argv["slip"] === "number"
  ) {
    const factor = argv.side === "long" ? 1 + argv.slip : 1 - argv.slip;
    priceGuard = toMicroUsd(argv["oracle-price"] * factor);
  } else if (typeof argv["max-price"] === "number" && argv.side === "long") {
    priceGuard = toMicroUsd(argv["max-price"]);
  } else if (typeof argv["min-price"] === "number" && argv.side === "short") {
    priceGuard = toMicroUsd(argv["min-price"]);
  }
  if (!priceGuard) {
    fail(
      "No price guardrail provided. Use --oracle-price + --slip or --max-price/--min-price.",
    );
    steps.fail("programPass", "Missing guardrail configuration");
    throw new Error("Guardrail configuration required");
  }

  bar("Amounts", "🧮");
  kv(
    "Size USD",
    `${argv["size-usd"].toFixed(6)} → ${sizeUsdDeltaDisc.toString()} μUSD`,
  );
  if (havePR) {
    kv(
      "Collateral",
      `${argv.collat} → ${collateralTokenDelta.toString()} raw (dec=${decimals})`,
    );
  } else {
    kv("Collateral", `0 (discovery mode; CLI input ${argv.collat})`);
  }
  kv("Guardrail", `${priceGuard.toString()} μUSD`);

  // Step 4 — Build & send — MANUAL TX to enforce instruction order
  bar("Submit", "📤");

  let eventAuthorityPk: PublicKey | null = null;
  try {
    [eventAuthorityPk] = PublicKey.findProgramAddressSync(
      [Buffer.from("__event_authority")],
      programId,
    );
  } catch {}

  const signer = (provider.wallet as any).payer as Keypair;
  let lastValidBlockHeight: number | undefined;
  let reqAtaInit: { ata: PublicKey; ix: any } | null = null;

  if (havePR) {
    await steps.time("ataRequest", async () => {
      const escrowTokenProgramId = await getTokenProgramIdForMint(collateralMint);
      reqAtaInit = createAtaIxStrict(
        wallet.publicKey,
        collateralMint,
        positionRequest,
        /*allowOwnerOffCurve=*/ true,
        escrowTokenProgramId,
      );
      console.log(`🧪 ATA debug (${mintLabel(collateralMint)}, positionRequest):`, {
        mint: shortId(collateralMint.toBase58()),
        owner: shortId(positionRequest.toBase58()),
        allowOwnerOffCurve: true,
        tokenProgramId: shortId(escrowTokenProgramId.toBase58()),
        ata: shortId(reqAtaInit.ata.toBase58()),
      });
      const expectedReqAta = deriveAtaStrict(
        collateralMint,
        positionRequest,
        true,
        escrowTokenProgramId,
      );
      if (!reqAtaInit.ata.equals(expectedReqAta)) {
        throw new Error("ATA mismatch (positionRequest) vs seed derivation");
      }
    });
    if (reqAtaInit) {
      steps.ok("ataRequest", shortId(reqAtaInit.ata.toBase58()));
    }
  } else {
    steps.start("ataRequest");
    steps.ok("ataRequest", "Skipped (discovery mode)");
  }

  const preIxs: any[] = [
    ComputeBudgetProgram.setComputeUnitLimit({ units: argv.cuLimit }),
    ComputeBudgetProgram.setComputeUnitPrice({
      microLamports: argv.priorityMicrolamports,
    }),
  ];

  if (collateralMint.equals(wsolMint)) {
    const ownerPubkey = owner.publicKey;
    const wsolAta = getAssociatedTokenAddressSync(
      wsolMint,
      ownerPubkey,
      /* allowOwnerOffCurve */ false,
      TOKEN_PROGRAM_ID,
      ASSOCIATED_TOKEN_PROGRAM_ID,
    );

    if (ownerPubkey.equals(wsolAta)) {
      throw new Error(
        "BUG: payer equals ATA (would cause 'from must not carry data').",
      );
    }

    const payerInfo = await provider.connection.getAccountInfo(ownerPubkey);
    if (!payerInfo || !payerInfo.owner.equals(SystemProgram.programId)) {
      throw new Error("BUG: payer is not a SystemProgram-owned account.");
    }

    preIxs.push(
      createAssociatedTokenAccountIdempotentInstruction(
        ownerPubkey,
        wsolAta,
        ownerPubkey,
        wsolMint,
        TOKEN_PROGRAM_ID,
        ASSOCIATED_TOKEN_PROGRAM_ID,
      ),
    );
  } else {
    preIxs.push(ownerAtaInit.ix);
  }
  if (reqAtaInit) preIxs.push(reqAtaInit.ix);

  console.log(
    "🧾 preIxs =",
    preIxs.length,
    havePR ? " (owner + req escrow)" : " (owner only)",
  );

  const metas4 = (ix: any) =>
    ix?.keys?.slice(0, 4)?.map((k: any) => k.pubkey.toBase58());
  if (reqAtaInit)
    console.log(
      "AToken escrow[req] metas [payer, ata, owner, mint] =",
      metas4(reqAtaInit.ix),
    );

  if (!eventAuthorityPk) {
    throw new Error("Missing event authority PDA");
  }

  const positionRequestUsdcAta =
    havePR && reqAtaInit ? reqAtaInit.ata : ownerAtaInit.ata;

  const buildAccountsStrictBase = () => ({
    owner: wallet.publicKey,
    fundingAccount: ownerAtaInit.ata,
    perpetuals: perpetuals.publicKey,
    pool: pool.publicKey,
    position: positionPk,
    positionRequest,
    positionRequestAta: positionRequestUsdcAta,
    custody: marketCustodyPk,
    collateralCustody: collateralCustodyPk,
    inputMint: collateralMint,
    referral: wallet.publicKey,
    tokenProgram: TOKEN_PROGRAM_ID,
    associatedTokenProgram: ASSOCIATED_TOKEN_PROGRAM_ID,
    systemProgram: SystemProgram.programId,
    eventAuthority: eventAuthorityPk!,
    program: program.programId,
  });

  steps.start("positionSelect");
  const previewMode: "idl" | "swapped" = flipCustodyOrder ? "swapped" : "idl";
  const previewAccountsBase = buildAccountsStrictBase();
  const previewAccounts =
    previewMode === "swapped"
      ? {
          ...previewAccountsBase,
          custody: collateralCustodyPk,
          collateralCustody: marketCustodyPk,
        }
      : previewAccountsBase;
  steps.ok(
    "positionSelect",
    `${previewMode === "swapped" ? "Swapped" : "IDL"} custody → ${shortId(positionPk.toBase58())}`,
  );
  console.log(
    "💳 fundingAccount (payer) =",
    previewAccounts.fundingAccount.toBase58(),
    "(collateral ATA)",
  );

  const postIxs: web3.TransactionInstruction[] = [];
  const ixArgs = {
    sizeUsdDelta: sizeUsdDeltaDisc,
    collateralTokenDelta,
    side: sideEnum,
    priceSlippage: priceGuard,
    jupiterMinimumOut: null,
  };

  await rpcPool.runWithFailover(
    async (conn) => {
      await ensureProviderOnConnection(conn);

      const dryRunMode: "idl" | "swapped" = previewMode;
      if (argv["dry-run"]) {
        const dryRunPosition = positionPk;
        const dryRunPreIxs = (() => {
          steps.start("ataPosition");
          const { ix: posAtaIx } = makePositionUsdcAtaIx(
            wallet.publicKey,
            dryRunPosition,
            collateralMint,
          );
          const rebuilt = [...preIxs, posAtaIx];
          steps.ok(
            "ataPosition",
            `Dry-run for ${shortId(dryRunPosition.toBase58())}`,
          );
          return rebuilt;
        })();
        const accountsBase = buildAccountsStrictBase();
        const accounts =
          dryRunMode === "swapped"
            ? {
                ...accountsBase,
                custody: collateralCustodyPk,
                collateralCustody: marketCustodyPk,
              }
            : accountsBase;
        steps.ok(
          "accountsBuilt",
          `Dry-run ${dryRunMode === "swapped" ? "swapped" : "idl"}`,
        );
        const method = (program as any).methods
          .createIncreasePositionMarketRequest(ixArgs)
          .accountsStrict(accounts)
          .preInstructions(dryRunPreIxs)
          .postInstructions(postIxs);

        const label =
          dryRunMode === "swapped" ? "dry-run (swapped)" : "dry-run";
        const reqIx = await debugPrintIx(program as Program, method, label);

        const allIxs = [...dryRunPreIxs, reqIx, ...postIxs];
        const { blockhash, lastValidBlockHeight: lvbh } =
          await provider.connection.getLatestBlockhash();
        lastValidBlockHeight = lvbh;
        const message = new TransactionMessage({
          payerKey: signer.publicKey,
          recentBlockhash: blockhash,
          instructions: allIxs,
        }).compileToV0Message();
        const tx = new VersionedTransaction(message);
        tx.sign([signer]);

        await steps.time(
          "simulate",
          async () => simulateOrSend(provider.connection, tx, true),
          "Dry-run executed",
        );
        return true;
      }

      const finalPositionPk = await sendIncreasePositionRobust({
        program: program as Program,
        preIxs,
        postIxs,
        ixArgs,
        payer: wallet.publicKey,
        marketCustodyPk,
        collateralCustodyPk,
        collateralMintPk: collateralMint,
        derived: DERIVED,
        orderMode: previewMode,
        buildAccountsStrictBase,
      }, steps);
      steps.ok("positionSelect", `Final ${shortId(finalPositionPk.toBase58())}`);
      return true;
    },
    "send/createIncreasePositionMarketRequest",
  );

  if (argv["dry-run"]) {
    info("🧪", "Simulation only (dry-run)");
    console.log({ lastValidBlockHeight });
    steps.ok("watch", "Skipped (dry-run)");
    return;
  }

  ok("Tx sent (see signature above)");
  info(
    "📝",
    `PositionRequest = ${positionRequest.toBase58()}  (keeper will execute)\n`,
  );
  steps.ok("watch", "Keeper will execute request");
  } catch (err) {
    const programPassRow = steps.get("programPass");
    if (!programPassRow) {
      steps.fail("programPass", "Program rejected (see logs)");
    }
    throw err;
  } finally {
    steps.print("Order Placement Checklist");
  }
})();

// --- drop-in replacement for simulateOrSend ---
async function simulateOrSend(
  connection: import("@solana/web3.js").Connection,
  tx: import("@solana/web3.js").VersionedTransaction,
  dryRun: boolean,
) {
  if (dryRun) {
    console.log("🧪 dry-run: simulating transaction (no send)");
    const sim = await connection.simulateTransaction(tx, {
      sigVerify: false,
      replaceRecentBlockhash: true,
    });
    if (sim.value.err) console.error("❌ simulate err:", sim.value.err);
    if (sim.value.logs?.length) {
      console.log("🧾 simulate logs (compact):");
      for (const l of formatLogs(sim.value.logs)) console.log("   ", l);
    }
    if (!sim.value.err) {
      console.log("✅ simulation success");
    }
    return;
  }

  try {
    const sig = await connection.sendTransaction(tx, {
      skipPreflight: false,
      maxRetries: 3,
    });
    console.log("✅ sent:", sig);
  } catch (err: any) {
    console.error("❌ sendTransaction error:", err);
    if (typeof err.getLogs === "function") {
      const logs = await err.getLogs().catch(() => null);
      if (logs?.length) {
        console.error("🧾 send logs (compact):");
        for (const l of formatLogs(logs)) console.error("   ", l);
      }
    } else if (err?.transactionLogs?.length) {
      console.error("🧾 send logs (compact):");
      for (const l of formatLogs(err.transactionLogs)) console.error("   ", l);
    }
    throw err;
  }
}

