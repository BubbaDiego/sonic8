import type { Idl } from "@coral-xyz/anchor";
import { PublicKey } from "@solana/web3.js";
import BN from "bn.js";
import { warn } from "../utils/logger.js";

// ————————————————————————————————————————————————————————————————————————
// Amount helpers
// ————————————————————————————————————————————————————————————————————————

export const ONE = new BN(1);
export const ZERO = new BN(0);

export function toMicroUsd(v: number): BN {
  return new BN(Math.round(v * 1e6));
}

export function toTokenAmount(ui: number, decimals: number): BN {
  const s = ui.toString();
  const [i, f = ""] = s.split(".");
  const frac = (f + "0".repeat(decimals)).slice(0, decimals);
  return new BN(i).mul(new BN(10).pow(new BN(decimals))).add(new BN(frac));
}

export function fromTokenAmount(raw: BN, decimals: number): string {
  const base = new BN(10).pow(new BN(decimals));
  const i = raw.div(base).toString();
  const f = raw.mod(base).toString().padStart(decimals, "0").replace(/0+$/, "");
  return f.length ? `${i}.${f}` : i;
}

// ————————————————————————————————————————————————————————————————————————
// PDA derivation via IDL seeds (with safe fallback)
// ————————————————————————————————————————————————————————————————————————

type Seed = any;

function seedsFromIdl(idl: Idl, accountName: string): Seed[] | null {
  const acc = (idl as any).accounts?.find((a: any) => (a.name?.toLowerCase?.() === accountName.toLowerCase()));
  return acc?.pda?.seeds ?? null;
}

function u64LE(n: number | bigint) {
  const b = Buffer.alloc(8);
  b.writeBigUInt64LE(BigInt(n));
  return b;
}

function seedBuf(seed: any, ctx: Record<string, any>): Buffer {
  if (seed.kind === "const") {
    if (typeof seed.value === "string") return Buffer.from(seed.value);
    if (Array.isArray(seed.value)) return Buffer.from(seed.value);
    if (seed.bytes) return Buffer.from(seed.bytes);
  }
  if (seed.kind === "account") {
    const pk = ctx[seed.path] || ctx[seed.account] || ctx[seed.name];
    if (!pk) throw new Error(`Missing account for seed.path=${seed.path}`);
    return (pk as PublicKey).toBuffer();
  }
  if (seed.kind === "arg") {
    const v = ctx[seed.path] ?? ctx[seed.name] ?? ctx[seed.arg] ?? ctx["seed"];
    if (typeof v === "number" || typeof v === "bigint") return u64LE(v);
    if (typeof v === "string") return Buffer.from(v);
    if (Buffer.isBuffer(v)) return v;
    throw new Error(`Missing arg seed ${seed.path}`);
  }
  throw new Error(`Unsupported seed kind: ${JSON.stringify(seed)}`);
}

export function derivePdaFromIdl(idl: Idl, programId: PublicKey, accountName: string, ctx: Record<string, any>): [PublicKey, number] {
  const seeds = seedsFromIdl(idl, accountName);
  if (seeds?.length) {
    try {
      const bufs = seeds.map((s: any) => seedBuf(s, ctx));
      return PublicKey.findProgramAddressSync(bufs, programId);
    } catch (e) {
      warn(`IDL seeds present for ${accountName} but failed to build: ${(e as Error).message}`);
    }
  } else {
    warn(`No IDL seeds for ${accountName}; falling back to heuristic`);
  }
  // Conservative heuristic:
  const label = accountName.toLowerCase().includes("request") ? "position_request" : "position";
  const owner = ctx["owner"];
  const pool = ctx["pool"];
  const custody = ctx["custody"];
  const collateralCustody = ctx["collateralCustody"];
  const seedList = [Buffer.from(label), owner.toBuffer(), pool.toBuffer(), custody.toBuffer(), collateralCustody.toBuffer()];
  if (accountName.toLowerCase().includes("request")) {
    seedList.push(u64LE(ctx["seed"] ?? Math.floor(Date.now() / 1000)));
  }
  return PublicKey.findProgramAddressSync(seedList, programId);
}

// Hard-coded once discovered via the seed bruteforcer tool.
export function derivePositionPda(
  programId: PublicKey,
  owner: PublicKey,
  pool: PublicKey,
): [PublicKey, number] {
  const seeds = [
    Buffer.from("position"),
    owner.toBuffer(),
    pool.toBuffer(),
  ];
  return PublicKey.findProgramAddressSync(seeds, programId);
}

export function sideToEnum(side: string) {
  const s = side.toLowerCase();
  if (s === "long") return { long: {} };
  if (s === "short") return { short: {} };
  throw new Error(`Invalid --side ${side}`);
}

export function requestTypeMarket() { return { market: {} }; }
