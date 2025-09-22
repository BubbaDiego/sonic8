import fs from "fs";
import path from "path";
import bs58 from "bs58";
import { AnchorProvider, Program, Wallet } from "@coral-xyz/anchor";
import { Connection, Keypair, PublicKey, SystemProgram, } from "@solana/web3.js";
import { getAssociatedTokenAddressSync, createAssociatedTokenAccountInstruction, getAccount, createSyncNativeInstruction, NATIVE_MINT, TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID, } from "@solana/spl-token";
import BN from "bn.js";
import { info, kv, ok, warn, bar } from "../utils/logger.js";
import { IDL as JUP_PERPS_IDL } from "../idl/jupiter-perpetuals-idl.js";
export const SYS = { SystemProgram, TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID };
export const MINTS = {
    WSOL: NATIVE_MINT,
    SOL: NATIVE_MINT,
    USDC: new PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
    USDT: new PublicKey("Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"),
    WETH: new PublicKey("7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs"),
};
export function loadKeypair(filePath) {
    const p = path.resolve(filePath);
    const raw = fs.readFileSync(p, "utf8").trim();
    try {
        const j = JSON.parse(raw);
        if (Array.isArray(j))
            return Keypair.fromSecretKey(Uint8Array.from(j));
        if (typeof j === "object" && j !== null) {
            const b58 = j.privateKey || j.secretKey;
            if (typeof b58 === "string")
                return Keypair.fromSecretKey(bs58.decode(b58));
        }
        throw new Error("Unrecognized keypair JSON format");
    }
    catch (e) {
        try {
            return Keypair.fromSecretKey(bs58.decode(raw));
        }
        catch { }
        throw e;
    }
}
export function bootstrap(rpc, keypairPath) {
    bar("Bootstrap", "🔗");
    const connection = new Connection(rpc, { commitment: "confirmed" });
    const kp = loadKeypair(keypairPath);
    const wallet = new Wallet(kp);
    const provider = new AnchorProvider(connection, wallet, { commitment: "confirmed" });
    const meta = JUP_PERPS_IDL?.metadata;
    const programId = new PublicKey(meta?.address ?? (() => { throw new Error("IDL.metadata.address missing; update IDL"); })());
    const program = new Program(JUP_PERPS_IDL, programId, provider);
    info("🧭", `Network: ${rpc}`);
    kv("Owner", wallet.publicKey.toBase58());
    kv("Program", programId.toBase58());
    ok("IDL loaded and program ready");
    return { connection, wallet, provider, programId, program };
}
export async function getSingletonPerpetuals(program) {
    bar("Fetch Perpetuals (singleton)", "📦");
    const all = await program.account.perpetuals.all();
    if (!all?.length)
        throw new Error("No Perpetuals account found");
    if (all.length > 1)
        warn(`Found ${all.length} Perpetuals accounts; using first`);
    const perp = all[0];
    kv("Perpetuals", perp.publicKey.toBase58());
    return perp;
}
export async function getSingletonPool(program) {
    bar("Fetch Pool (singleton)", "🏦");
    const pools = await program.account.pool.all();
    if (!pools?.length)
        throw new Error("No Pool accounts found");
    if (pools.length > 1)
        warn(`Found ${pools.length} pools; using first`);
    const pool = pools[0];
    kv("Pool", pool.publicKey.toBase58());
    return pool;
}
export async function getCustodies(program, poolAccount) {
    const out = [];
    for (const pk of poolAccount.custodies) {
        const acc = await program.account.custody.fetch(pk);
        out.push({ pubkey: pk, account: acc });
    }
    info("🧱", `Loaded ${out.length} custody accounts`);
    return out;
}
export async function findCustodyByMint(program, poolAccount, mint) {
    const custodies = await getCustodies(program, poolAccount);
    const found = custodies.filter(c => c.account.mint.toBase58() === mint.toBase58());
    if (found.length === 0)
        throw new Error(`No custody found for mint ${mint.toBase58()}`);
    if (found.length > 1)
        warn(`Multiple custodies for mint ${mint.toBase58()}, using first`);
    return found[0];
}
// Derive the ATA address we will pass as an account to Perps (works for PDAs when allowOwnerOffCurve=true)
function deriveAta(mint, owner, allowOwnerOffCurve) {
    return getAssociatedTokenAddressSync(mint, owner, allowOwnerOffCurve, TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID);
}
// Always use SPL’s explicit-ATA signature to build the create instruction.
// This ensures the exact key order/meta the ATA program expects across versions.
function createAtaIxExplicit(payer, ata, owner, mint) {
    return createAssociatedTokenAccountInstruction(payer, ata, owner, mint, TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID);
}
export async function ensureAtaIx(connection, mint, owner, payer) {
    const ata = deriveAta(mint, owner, /*offCurve*/ false);
    try {
        await getAccount(connection, ata);
        return { ata, ixs: [] };
    }
    catch {
        info("🪙", `Create ATA: ${ata.toBase58()}`);
        return { ata, ixs: [createAtaIxExplicit(payer, ata, owner, mint)] };
    }
}
export async function ensureAtaForOwner(connection, mint, owner, payer, allowOwnerOffCurve) {
    const ata = deriveAta(mint, owner, allowOwnerOffCurve);
    try {
        await getAccount(connection, ata);
        return { ata, ixs: [] };
    }
    catch {
        info("🪙", `Create ATA (owner offCurve=${allowOwnerOffCurve}): ${ata.toBase58()}`);
        return { ata, ixs: [createAtaIxExplicit(payer, ata, owner, mint)] };
    }
}
export async function topUpWsolIfNeededIx(connection, ata, owner, lamportsNeeded) {
    const curr = await getAccount(connection, ata).catch(() => undefined);
    const have = curr ? BigInt(curr.amount.toString()) : 0n;
    const delta = lamportsNeeded > have ? (lamportsNeeded - have) : 0n;
    const ixs = [];
    if (delta > 0n) {
        ixs.push(SystemProgram.transfer({ fromPubkey: owner, toPubkey: ata, lamports: Number(delta) }));
        ixs.push(createSyncNativeInstruction(ata));
        info("💧", `Wrap/top-up WSOL: need ${delta} lamports`);
    }
    return ixs;
}
// re-export BN so examples can `new cfg.BN(0)`
export { BN };
//# sourceMappingURL=perps.js.map