import fs from "fs";
import path from "path";
import bs58 from "bs58";
import type { Idl } from "@coral-xyz/anchor";
import { AnchorProvider, Program, Wallet } from "@coral-xyz/anchor";
import {
  Connection,
  Keypair,
  PublicKey,
  SystemProgram,
  TransactionInstruction,
  SYSVAR_RENT_PUBKEY,
} from "@solana/web3.js";
import {
  getAssociatedTokenAddressSync,
  createAssociatedTokenAccountInstruction,
  getAccount,
  createSyncNativeInstruction,
  NATIVE_MINT,
  TOKEN_PROGRAM_ID,
  ASSOCIATED_TOKEN_PROGRAM_ID,
} from "@solana/spl-token";
import BN from "bn.js";
import { info, kv, ok, warn, bar } from "../utils/logger.js";
import { IDL as JUP_PERPS_IDL } from "../idl/jupiter-perpetuals-idl.js";

export type PerpsCtx = {
  connection: Connection;
  wallet: Wallet;
  provider: AnchorProvider;
  programId: PublicKey;
  program: Program<Idl>;
};

export const SYS = { SystemProgram, TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID };

export const MINTS = {
  WSOL: NATIVE_MINT,
  SOL: NATIVE_MINT,
  USDC: new PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
  USDT: new PublicKey("Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"),
  WETH: new PublicKey("7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs"),
};

export function loadKeypair(filePath: string): Keypair {
  const p = path.resolve(filePath);
  const raw = fs.readFileSync(p, "utf8").trim();
  try {
    const j = JSON.parse(raw);
    if (Array.isArray(j)) return Keypair.fromSecretKey(Uint8Array.from(j));
    if (typeof j === "object" && j !== null) {
      const b58 = (j as any).privateKey || (j as any).secretKey;
      if (typeof b58 === "string") return Keypair.fromSecretKey(bs58.decode(b58));
    }
    throw new Error("Unrecognized keypair JSON format");
  } catch (e) {
    try { return Keypair.fromSecretKey(bs58.decode(raw)); } catch {}
    throw e;
  }
}

export function bootstrap(rpc: string, keypairPath: string): PerpsCtx {
  bar("Bootstrap", "🔗");
  const connection = new Connection(rpc, { commitment: "confirmed" });
  const kp = loadKeypair(keypairPath);
  const wallet = new Wallet(kp);
  const provider = new AnchorProvider(connection, wallet, { commitment: "confirmed" });

  const meta = (JUP_PERPS_IDL as any)?.metadata;
  const programId = new PublicKey(
    meta?.address ?? (() => { throw new Error("IDL.metadata.address missing; update IDL"); })()
  );
  const program = new Program(JUP_PERPS_IDL as Idl, programId, provider);

  info("🧭", `Network: ${rpc}`);
  kv("Owner", wallet.publicKey.toBase58());
  kv("Program", programId.toBase58());
  ok("IDL loaded and program ready");
  return { connection, wallet, provider, programId, program };
}

export async function getSingletonPerpetuals(program: Program) {
  bar("Fetch Perpetuals (singleton)", "📦");
  const all = await (program.account as any).perpetuals.all();
  if (!all?.length) throw new Error("No Perpetuals account found");
  if (all.length > 1) warn(`Found ${all.length} Perpetuals accounts; using first`);
  const perp = all[0];
  kv("Perpetuals", perp.publicKey.toBase58());
  return perp as { publicKey: PublicKey; account: any };
}

export async function getSingletonPool(program: Program) {
  bar("Fetch Pool (singleton)", "🏦");
  const pools = await (program.account as any).pool.all();
  if (!pools?.length) throw new Error("No Pool accounts found");
  if (pools.length > 1) warn(`Found ${pools.length} pools; using first`);
  const pool = pools[0];
  kv("Pool", pool.publicKey.toBase58());
  return pool as { publicKey: PublicKey; account: any };
}

export async function getCustodies(program: Program, poolAccount: any) {
  const out: { pubkey: PublicKey; account: any }[] = [];
  for (const pk of poolAccount.custodies as PublicKey[]) {
    const acc = await (program.account as any).custody.fetch(pk);
    out.push({ pubkey: pk, account: acc });
  }
  info("🧱", `Loaded ${out.length} custody accounts`);
  return out;
}

export async function findCustodyByMint(program: Program, poolAccount: any, mint: PublicKey) {
  const custodies = await getCustodies(program, poolAccount);
  const found = custodies.filter(c => (c.account.mint as PublicKey).toBase58() === mint.toBase58());
  if (found.length === 0) throw new Error(`No custody found for mint ${mint.toBase58()}`);
  if (found.length > 1) warn(`Multiple custodies for mint ${mint.toBase58()}, using first`);
  return found[0];
}

function createAtaIxExplicit(
  payer: PublicKey,
  ata: PublicKey,
  owner: PublicKey,
  mint: PublicKey,
): TransactionInstruction {
  // Use spl-token’s explicit-ATA signature. It generates the exact
  // account metas the Associated Token Program expects on all versions.
  return createAssociatedTokenAccountInstruction(
    payer, ata, owner, mint, TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
  );
}

function deriveAta(
  mint: PublicKey,
  owner: PublicKey,
  allowOwnerOffCurve: boolean,
): PublicKey {
  return getAssociatedTokenAddressSync(
    mint, owner, allowOwnerOffCurve, TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
  );
}

export async function ensureAtaIx(
  connection: Connection, mint: PublicKey, owner: PublicKey, payer: PublicKey
) {
  const ata = deriveAta(mint, owner, /*offCurve*/ false);
  try {
    await getAccount(connection, ata);
    return { ata, ixs: [] as any[] };
  } catch {
    info("🪙", `Create ATA: ${ata.toBase58()}`);
    return { ata, ixs: [createAtaIxExplicit(payer, ata, owner, mint)] };
  }
}

export async function ensureAtaForOwner(
  connection: Connection, mint: PublicKey, owner: PublicKey, payer: PublicKey, allowOwnerOffCurve: boolean
) {
  const ata = deriveAta(mint, owner, allowOwnerOffCurve);
  try {
    await getAccount(connection, ata);
    return { ata, ixs: [] as any[] };
  } catch {
    info("🪙", `Create ATA (owner offCurve=${allowOwnerOffCurve}): ${ata.toBase58()}`);
    return { ata, ixs: [createAtaIxExplicit(payer, ata, owner, mint)] };
  }
}

export async function topUpWsolIfNeededIx(connection: Connection, ata: PublicKey, owner: PublicKey, lamportsNeeded: bigint) {
  const curr = await getAccount(connection, ata).catch(() => undefined);
  const have = curr ? BigInt(curr.amount.toString()) : 0n;
  const delta = lamportsNeeded > have ? (lamportsNeeded - have) : 0n;
  const ixs = [] as any[];
  if (delta > 0n) {
    ixs.push(SystemProgram.transfer({ fromPubkey: owner, toPubkey: ata, lamports: Number(delta) }));
    ixs.push(createSyncNativeInstruction(ata));
    info("💧", `Wrap/top-up WSOL: need ${delta} lamports`);
  }
  return ixs;
}

// re-export BN so examples can `new cfg.BN(0)`
export { BN };
