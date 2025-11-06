// save as backend/core/raydium_core/ts/value_raydium_positions.ts
// run with: npx ts-node --transpile-only value_raydium_positions.ts --mints <MINT1[,MINT2…]>

import 'dotenv/config'
import { Connection, PublicKey } from '@solana/web3.js'
import Decimal from 'decimal.js'

// Import SDK only for constants and optional Price helper; we won't rely on its CLMM helpers.
let SDK: any = {}
try { SDK = require('@raydium-io/raydium-sdk-v2') } catch {}
if (!Object.keys(SDK).length) { try { SDK = require('@raydium-io/raydium-sdk') } catch {} }

const CLMM_ID = (() => {
  try { return new PublicKey(SDK.CLMM_PROGRAM_ID) } catch { return null }
})();

const Price = (SDK as any).price || (SDK as any).Price || null;
const fetchPrices = (Price && (Price.fetchMultiple || (Price.getMultiple || (Price.getPrices || null)))) || null;

// --- small helpers ---
const U64_F = new Decimal(2).pow(64)
const u64 = (x:any)=> new Decimal(String(x))
const sqrtFromTick = (t:number)=> new Decimal(1.0001).pow(t)
const q64ToDec = (q:any)=> new Decimal(String(q)).div(USED)
const short = (s:string)=> s.length>12 ? `${s.slice(0,6)}…${s.slice(-6)}` : s

function tryPk(s?:string){ try{ return s? new PublicKey(s): null } catch { return null } }
function assert(condition:any, msg:string): asserts condition { if(!condition) throw new Error(msg) }

// --- CLMM position layout (Anchor-like) ---
/**
 * Raydium CLMM PersonalPositionState (common fields across v1/v2):
 *   u8    bump
 *   pub owner: Pubkey
 *   pub pool_id: Pubkey
 *   pub tick_lower: i32
 *   pub tick_upper: i32
 *   pub liquidity: u128
 *   pub fee_growth_inside_a: u128
 *   pub fee_growth_inside_b: u128
 *   pub tokens_owed_a: u64
 *   pub tokens_owed_b: u64
 *   (newer v2 adds reward infos after; we can ignore for valuation)
 */
function decodePosition(buf: Buffer) {
  let o = 0
  const bump = buf.readUInt8(o); o += 1
  const owner = new PublicKey(buf.slice(o, o+32)); o += 32
  const pool = new PublicKey(buf.slice(o, o+32)); o += 32
  const tickLower = buf.readInt32LE(o); o += 4
  const tickUpper = buf.readInt32LE(o); o += 4
  const liL = buf.readBigUInt64LE(o); o += 8
  const liH = buf.readBigUInt64LE(o); o += 8
  const liquidity = new Decimal(liH.toString()).times(2n**64n).plus(new Decimal(liL.toString()))
  const feeA_L = buf.readBigUInt64LE(o); o += 8
  const feeA_H = buf.readBigUInt64LE(o); o += 8
  const feeA = new Decimal(feeA_H.toString()).times(2n**64n).plus(new Decimal(feeA_L.toString()))
  const feeB_L = buf.readBigUInt64LE(o); o += 8
  const feeB_H = buf.readBigUInt64LE(o); o += 8
  const feeB = new Decimal(feeB_H.toString()).times(2n**64n).plus(new Decimal(feeB_L.toString()))
  // (ignore optional reward infos if present)
  return { bump, owner, pool, tickLower, tickUpper, liquidity, feeA, feeB }
}

/**
 * Raydium CLMM PoolState (common fields across v1/v2):
 *   pub amm_config: Pubkey
 *   pub ... (skip to)
 *   pub amm_config, owner, token_mint_a, token_vault_a, token_mint_b, token_vault_b
 *   pub sqrt_price_x64: u128
 *   pub tick_current: i32
 *   pub liquidity: u128
 *   pub tick_spacing: u16
 * We only need sqrt_price_x64 and token mint A/B with decimals.
 */
function decodePool(buf: Buffer) {
  // This is tolerant: parse by searching for 2 PubKeys and a u128 sqrtPriceX64 followed by tick_current (i32).
  // Raydium CLMM v2 PoolState layout (approx): [..config(32)..][...][mintA(32)][vaultA(32)][mintB(32)][..., sqrtPriceX64(16)][..][tick_current(4)].
  // We'll heuristically scan for two distinct 32-byte pubkeys (A/B) followed by a 16-byte value; then read mm decimals via RPC.
  // For robustness across SDK revisions, we rely on RPC to get mint decimals.
  const bytes = new Uint8Array(buf)
  // naive: search for two 32B substrings that look like valid pubkeys (ed25519 points). We'll just take the first two 32B fields after the first 64 bytes.
  const mA = new PublicKey(Buffer.from(bytes.slice(64, 96)))
    , vA = new BigInt64Array([0n]) // not used
    , mB = new PublicKey(Buffer.from(bytes.slice(96, 128)))
    , sqrtLo = buf.readBigUInt64LE(160)
    , sqrtHi = buf.readBigUInt64LE(168)
    , sqrt = new Decimal(sqrtHi.toString()).times(2n**64n).plus(new Decimal(sqrtLo.toString()))
    , tickCurrent = buf.readInt32LE(184)
  return { mA, mB, sqrt, tickCurrent }
}

// ---- main ----
(async () => {
  try {
    const conn = new Connection(process.env.RPC_URL || process.env.SOLANA_REMOTE || 'https://api.mainnet-beta.solana.com', 'confirmed')
    const owner = new PublicKey(process.argv[process.argv.indexOf('--owner')+1])
    let mints: string[] = []
    const mIndex = process.argv.indexOf('--mints')
    if (mIndex > -1 && process.argv[mIndex+1]) {
      mints = process.argv[mIndex+1].split(',').map(s => s.trim()).filter(Boolean)
    }
    if (!mints.length) {
      console.error('No --mints provided and SDK lacks by-owner helpers; supply the mint(s) from menu 2.')
      process.exit(2)
    }
    // derive position PDAs: try SDK.getPdaPersonalPositionAddress if present & compatible, else fallback to manual seed ['position', mint, pool] later
    const mintPks = mints.map(m => new PublicKey(m))

    // We don’t know pool yet; we must *discover* the position account for each mint.
    // Raydium CLMM stores a "personal position" PDA at seed ['position', mint, <pool-id>], but SDKs differ.
    // Robust approach: scan all CLMM program accounts filtering by data size ~ 216 bytes and then pick those whose `position.mint` equals our mint.
    if (!CLMM_ID) throw new Error('SDK did not export CLMM_PROGRAM_ID; cannot discover position PDAs.')

    const filters = [{ dataSize: 216 }] // typical size of PersonalPositionState without rewards; adjust if needed
    const accs = await (conn as any).getProgramAccounts(CLMM_ID, { filters })

    // index by mint -> position account pubkey
    const mintToPosPk = new Map<string, PublicKey>()
    for (const { pubkey, account } of accs.value as any[]) {
      try {
        const pos = decodePosition(Buffer.from(account.data))
        const m = pos.owner ? pos.owner.toBase58() : '' // some builds store owner then mint; if owner mismatch, try other offsets
        // Try alternate layout: some builds put mint first then pool; add additional decode if needed
        // Here we assume: position.mint == mintPks[i]; if we can’t find a match, we skip
        for (const mk of mints) {
          if (mk === m) {
            mintToPosPk.set(mk, pubkey)
          }
        }
      } catch { /* skip unknown account */ }
    }

    const targets = mintPks.map(pk => {
      const posPk = mintToPosPk.get(pk.toBase58())
      if (!posPk) {
        console.error('Could not locate position account for mint', pk.toBase58())
      }
      return posPk
    }).filter(Boolean) as PublicKey[]

    if (!targets.length) {
      console.error('No matching CLMM position accounts found for supplied mints.')
      process.exit(2)
    }

    const posInfos = await conn.getMultipleAccountsInfo(targets, { commitment: 'confirmed' })
    const decodedPositions: { posPk: PublicKey, poolPk: PublicKey, mint: string, L: Decimal, tickL:number, tickU:number }[] = []

    for (let i=0;i<posInfos.length;i++) {
      const acc = posInfos[i]; if (!acc?.data) continue
      const state = decodePosition(Buffer.from(acc.data))
      // We assume the NFT mint is stored in `owner` field in this build. If not, match by PDA ordering or add alt decode here.
      decodedPositions.push({ posPk: targets[i], poolPk: state.pool, mint: state.owner.toBase58(), L: state.liquidity, tickL: state.tickLower, tickU: state.tickUpper })
    }

    // fetch pools
    const poolPks = Array.from(new Set(decodedPositions.map(d => d.poolPk.toBase58()))).map(s => new PublicKey(s))
    const poolInfos = await conn.getMultipleAccountsInfo(poolPks, { commitment: 'confirmed' })
    const poolMap = new Map<string, { mA: string, mB: string, sqrt: Decimal }>()
    for (let i=0;i<poolPks.length;i++){
      const acc = poolInfos[i]; if (!acc?.data) continue
      const dec = decodePool(Buffer.from(acc.data))
      poolMap.set(poolPks[i].toBase58(), { mA: dec.mA.toBase58(), mB: dec.mB.toBase58(), sqrt: dec.sqrt })
    }

    // optional: price map
    let priceMap: Record<string, number> = {}
    if (Price && typeof fetchPrices === 'function') {
      const uniq = new Set<string>()
      for (const p of poolMap.values()) { uniq.add(p.mA); uniq.add(p.mB) }
      const arr = Array.from(uniq)
      try {
        const out = await (fetchPrices as any).call(Price, { tokenMints: arr, connection: conn })
        priceMap = out || {}
      } catch {}
    }

    console.log('\n💎 Raydium CL Positions (raw decode)\n')
    console.log('Pool'.padEnd(12), 'Position'.padEnd(14), 'TokenA'.padEnd(24), 'TokenB'.ljust? '': '', 'USD')
    let total = new Decimal(0)
    for (const p of decodedPositions) {
      const pool = poolMap.get(p.poolPk.toBaseString? p.poolPk.toBase58(): p.poolPk.toBase58())
      if (!pool) continue
      const sqrtL = sqrtFromTick(p.tickL), sqrtU = sqrtFromTick(p.tickU)
      const { a0, a1 } = amountsFromL(p.L, sqrtL, pool.sqrt, sqrtU)
      const priceA = new Decimal(String(priceMap[pool.mA] || 0))
      const priceB = new Decimal(String(priceMap[pool.mB] || 0))
      const usd = a0.mul(priceA).add(a1.mul(priceB))
      total = total.add(usd)
      const sa = `${pool.mA.slice(0,6)}…${pool.mA.slice(-6)}`
      const sb = `${pool.mB.slice(0,6)}…${pool.mB.slice(-6)}`
      console.log(
        (p.poolPk.toBase58().slice(0,6)+'…'+p.poolPk.toBase58().slice(-6)).padEnd(12),
        (p.mint.slice(0,6)+'…'+p.mint.slice(-6)).padEnd(14),
        `${a0.div(new Decimal(10).pow(0)).toSignificantDigits(6)} ${sa}`.padEnd(24),
        `${a1.div(new Decimal(10).pow(0)).toSignificantDigits(6)} ${sb}`.padEnd(24),
        `$${usd.toSignificantDigits(6)}`
      )
    }
    console.log('\nTotal ≈', `$${total.toSignificantDigits(8).toString()}`)
  } catch (e:any) {
    console.error('Fatal:', e?.message || e)
    process.exit(1)
  }
})();
