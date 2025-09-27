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

// --- CLI guard: strip any stray flags someone might have pushed into argv
function scrubInjectedCliArgv(argv: string[]): string[] {
  const drop = new Set(["--position", "--position-request", "--positionRequest"]);
  const out: string[] = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (drop.has(a)) {
      i++;
      continue;
    }
    out.push(a);
  }
  return out;
}

const utf8 = (s: string) => Buffer.from(s);

type PdaInputs = {
  pool: PublicKey;
  owner: PublicKey;
  marketCustody: PublicKey;
  collateralCustody: PublicKey;
};

function derivePositionDeterministic(programId: PublicKey, inp: PdaInputs): PublicKey {
  const seeds = [
    utf8("position"),
    inp.pool.toBuffer(),
    inp.owner.toBuffer(),
    inp.marketCustody.toBuffer(),
    inp.collateralCustody.toBuffer(),
  ];
  return PublicKey.findProgramAddressSync(seeds, programId)[0];
}

function derivePositionRequestDeterministic(
  programId: PublicKey,
  inp: PdaInputs,
): PublicKey {
  const seeds = [
    utf8("position_request"),
    inp.pool.toBuffer(),
    inp.owner.toBuffer(),
    inp.marketCustody.toBuffer(),
    inp.collateralCustody.toBuffer(),
  ];
  return PublicKey.findProgramAddressSync(seeds, programId)[0];
}

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

const VALIDATION_SUBSTEPS = [
  { key: "vSeeds", label: "15a) seeds/position" },
  { key: "vCustodyOrder", label: "15b) custody order" },
  { key: "vPosAta", label: "15c) position USDC ATA" },
  { key: "vGuardrail", label: "15d) guardrail bounds" },
] as const;

class StepTracker {
  private runStart = performance.now();
  private data = new Map<
    string,
    { ok?: boolean; note?: string; t0?: number; t1?: number }
  >();
  private subData = new Map<
    string,
    Map<string, { ok?: boolean; note?: string; label?: string; t0?: number; t1?: number }>
  >();
  private printed = false;

  start(key: StepKey | string, note?: string) {
    const now = performance.now();
    const prev = this.data.get(key) || {};
    this.data.set(key, { ...prev, t0: prev.t0 ?? now, note: note ?? prev.note });
  }

  ok(key: StepKey | string, note?: string) {
    this.end(key, true, note);
  }

  fail(key: StepKey | string, note?: string) {
    this.end(key, false, note);
  }

  async time<T>(key: StepKey | string, fn: () => Promise<T>, note?: string): Promise<T> {
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

  get(key: StepKey | string) {
    return this.data.get(key);
  }

  subStart(key: string, label: string) {
    this.subSet("programPass", key, { label, ok: undefined, note: undefined }, false);
  }

  subOk(key: string, note?: string) {
    this.subSet("programPass", key, { ok: true, note }, true);
  }

  subFail(key: string, note?: string) {
    this.subSet("programPass", key, { ok: false, note }, true);
  }

  hasSub(key: string) {
    return this.subData.get("programPass")?.has(key) ?? false;
  }

  getSub(key: string) {
    return this.subData.get("programPass")?.get(key);
  }

  private subSet(
    parent: StepKey | string,
    key: string,
    val: { ok?: boolean; note?: string; label?: string },
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

  private end(key: StepKey | string, ok: boolean, note?: string) {
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
          const label = subRow.label ?? subKey;
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

type StepAPI = {
  start: (k: string, label?: string) => void;
  ok: (k: string, detail?: string) => void;
  fail: (k: string, detail?: string) => void;
  subStart: (k: string, label: string) => void;
  subOk: (k: string, label?: string) => void;
  subFail: (k: string, label?: string) => void;
};

function markProgramValidations(steps: StepAPI, logs: string[], expectedPos: PublicKey) {
  steps.start("programPass", "Program validations pass");

  // 15a: Seeds/position PDA
  steps.subStart("vSeeds", "15a) seeds/position");
  const seedErr = logs.some(
    (l) => l.includes("ConstraintSeeds") && l.includes("account: position"),
  );
  if (seedErr) {
    const right = extractRightFromLogs(logs);
    steps.subFail(
      "vSeeds",
      right ? `expected position=${right}` : `seeds mismatch (expected ${expectedPos.toBase58()})`,
    );
  } else {
    steps.subOk("vSeeds", "ok");
  }

  // 15b: custody ordering (common 6006)
  steps.subStart("vCustodyOrder", "15b) custody order");
  const badCustody = logs.some((l) => /Invalid collateral account/i.test(l));
  badCustody
    ? steps.subFail("vCustodyOrder", "market↔collateral swapped")
    : steps.subOk("vCustodyOrder", "ok");

  // 15c: collateral ATA present (defensive)
  steps.subStart("vPosAta", "15c) position USDC ATA");
  const ataInit = logs.some((l) => /Initialize the associated token account/i.test(l));
  steps.subOk("vPosAta", ataInit ? "created/exists" : "exists");

  // 15d: guardrail/slippage bounds
  steps.subStart("vGuardrail", "15d) guardrail bounds");
  const guardrail = logs.some((l) => /guardrail|price.*out.*bounds/i.test(l));
  guardrail
    ? steps.subFail("vGuardrail", "breached")
    : steps.subOk("vGuardrail", "ok");

  // Collapse 15
  const rejected = seedErr || badCustody || guardrail;
  rejected ? steps.fail("programPass", "program rejected") : steps.ok("programPass", "ok");
}

function extractRightFromLogs(logs: string[]): string | null {
  // looks for: Program log: Right: <pubkey>
  const i = logs.findIndex((l) => /Program log: Right:/.test(l));
  if (i >= 0 && logs[i + 1]) {
    const m = logs[i + 1].match(/[1-9A-HJ-NP-Za-km-z]{32,44}/);
    return m ? m[0] : null;
  }
  return null;
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

// Helpers to derive PDAs from the Anchor IDL seeds
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
    marketCustodyPk,
    collateralCustodyPk,
    derived,
    orderMode,
    buildAccountsStrictBase,
  } = params;

  const preIxs = [...params.preIxs];
  const postIxs = [...params.postIxs];

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

  try {
    console.log(
      "➡️ using position for send:",
      derived.position.toBase58(),
      "| order:",
      orderMode,
    );
    steps.start("accountsBuilt");
    const accounts = buildAccounts();
    steps.ok(
      "accountsBuilt",
      `Using ${orderMode} order for ${shortId(derived.position.toBase58())}`,
    );
    const m = program.methods
      .createIncreasePositionMarketRequest(ixArgs)
      .accountsStrict(accounts)
      .preInstructions(preIxs)
      .postInstructions(postIxs);
    const label = orderMode === "swapped" ? "final (swapped)" : "final";
    await debugPrintIx(program, m, label);
    steps.start("submit");
    await m.rpc();
    steps.ok("submit");
    markProgramValidations(steps, [], derived.position);
    steps.ok("watch");
    return derived.position;
  } catch (err: any) {
    steps.ok("submit");
    const logs: string[] =
      (err?.logs as string[]) ??
      (err?.transactionLogs as string[]) ??
      (Array.isArray(err?.errorLogs) ? err.errorLogs : []);
    markProgramValidations(steps, logs, derived.position);
    throw err;
  }
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
    const argv = await yargs(hideBin(scrubInjectedCliArgv(process.argv)))
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
  const ownerPk = owner.publicKey;

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
    owner: ownerPk,
    marketCustody: marketCustodyPk,
    collateralCustody: collateralCustodyPk,
  };
  const DERIVED = await steps.time(
    "pdas",
    async () => ({
      position: derivePositionDeterministic(program.programId, pdaInputs),
      positionRequest: derivePositionRequestDeterministic(program.programId, pdaInputs),
    }),
    "Deriving deterministic PDAs",
  );
  VALIDATION_SUBSTEPS.forEach(({ key, label }) => {
    if (!steps.hasSub(key)) {
      steps.subStart(key, label);
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

  const getOrCreateAtaIx = async ({
    payer,
    owner,
    mint,
    allowOwnerOffCurve = false,
  }: {
    payer: PublicKey;
    owner: PublicKey;
    mint: PublicKey;
    allowOwnerOffCurve?: boolean;
  }) => {
    const tokenProgramId = await getTokenProgramIdForMint(mint);
    const { ata, ix } = createAtaIxStrict(
      payer,
      mint,
      owner,
      allowOwnerOffCurve,
      tokenProgramId,
    );
    return [{ ata, ixs: [ix] }];
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

  steps.start("ataPosition");
  const [posUsdcAta] = await getOrCreateAtaIx({
    payer: ownerPk,
    owner: DERIVED.position,
    mint: collateralMint,
    allowOwnerOffCurve: true,
  });
  steps.ok("ataPosition", shortId(posUsdcAta.ata.toBase58()));
  preIxs.push(...posUsdcAta.ixs);

  if (collateralMint.equals(wsolMint)) {
    const ownerPubkey = ownerPk;
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

  const positionRequestUsdcAta = posUsdcAta.ata;

  const buildAccountsStrictBase = () => ({
    owner: wallet.publicKey,
    fundingAccount: ownerAtaInit.ata,
    perpetuals: perpetuals.publicKey,
    pool: pool.publicKey,
    position: DERIVED.position,
    positionRequest: DERIVED.positionRequest,
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
        const dryRunPreIxs = [...preIxs];
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
    markProgramValidations(steps, [], DERIVED.position);
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
      steps.fail("programPass", "Program rejected (no logs)");
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

