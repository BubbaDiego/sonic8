// @ts-nocheck
import 'dotenv/config'
import { Connection, PublicKey } from '@solana/web3.js'
import Decimal from 'decimal.js'

// Load Raydium SDK (v2 if present, else v1) for layout types and optional pricing.
// We do NOT call SDK.getPda*, SDK.toToken*, etc., to avoid version-specific pitfalls.
let SDK: any = {}
try { SDK = require('@raydium-io/raydium-sdk-v2') } catch {}
if (!Object.keys(SDK || {}).length) { try { SDK = require('@raydium-io/raydium-sdk') } catch {} }
if (!Object.keys(SDK || {}).length) {
  console.error('❌ Missing @raydium-io/raydium-sdk[_v2]. npm i in this folder.')
  process.exit(2)
}

const PositionInfoLayout =
  SDK.PositionInfo ||
  SDK.PositionLayout ||
  SDK.PositionInfoLayout ||
  SDK.ProtocolPositionLayout
const PoolInfoLayout =
  SDK.PoolInfo ||
  SDK.PoolLayout ||
  SDK.ClmmPoolInfo ||
  SDK.ClmmPoolInfoLayout
if (!PositionInfoLayout || !PoolInfoLayout) {
  console.error('❌ SDK missing Position/Pool layout exports. Keys:', Object.keys(SDK))
  process.exit(2)
}

const Price = (SDK as any).Price || (SDK as any).price || {}
const priceFetch: Function | null =
  (Price && (Price.fetchMultiple || Price.getMultiple || Price.getPrices)) || null

const RPC = process.env.RPC_URL || process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com'
const args = process.argv.slice(2)
const arg = (k: string) => {
  const i = args.indexOf(k)
  return i >= 0 ? args[i + 1] : undefined
}
const ownerStr = arg('--owner')
const mintsCsv = arg('--mints')
const owner = ownerStr ? new PublicKey(ownerStr) : null
const inputMints = (mintsCsv ? mintsCsv.split(',').map((s) => s.trim()).filter(Boolean) : []) as string[]

const TWO_64 = new Decimal(2).pow(64)
const ONE_0001 = new Decimal('1.0001')
const short = (s: string) => (s.length <= 12 ? s : `${s.slice(0, 6)}…${s.slice(-6)}`)

const q64ToDecimal = (q: any) => new Decimal(q.toString()).div(TWO_64)
const sqrtPriceFromTick = (tick: number) => ONE_0001.pow(tick).sqrt()

function amountsFromLiquidity(L: Decimal, sqrtLower: Decimal, sqrtCur: Decimal, sqrtUpper: Decimal) {
  if (sqrtCur.lte(sqrtLower)) {
    const amt0 = L.mul(sqrtUpper.minus(sqrtLower)).div(sqrtLower.mul(sqrtUpper))
    return { amt0, amt1: new Decimal(0) }
  }
  if (sqrtCur.gte(sqrtUpper)) {
    const amt1 = L.mul(sqrtUpper.minus(sqrtLower))
    return { amt0: new Decimal(0), amt1 }
  }
  const amt0 = L.mul(sqrtUpper.minus(sqrtCur)).div(sqrtUpper.mul(sqrtCur))
  const amt1 = L.mul(sqrtCur.minus(sqrtLower))
  return { amt0, amt1 }
}

const tryPublicKey = (input?: string) => {
  try {
    return input ? new PublicKey(input) : null
  } catch {
    return null
  }
}

const toPublicKey = (value: any): PublicKey => {
  if (!value) throw new Error('missing public key')
  if (value instanceof PublicKey) return value
  if (typeof value === 'string') return new PublicKey(value)
  if (value.toBase58) return new PublicKey(value.toBase58())
  if (value.toString && typeof value.toString === 'function') {
    const str = value.toString()
    if (str && str.length >= 32) return new PublicKey(str)
  }
  if (value instanceof Uint8Array || Buffer.isBuffer(value)) return new PublicKey(value)
  if (Array.isArray(value)) return new PublicKey(Buffer.from(value))
  throw new Error('unsupported public key input')
}

const extractProgramId = (): PublicKey => {
  const candidates: any[] = [
    (SDK as any).CLMM_PROGRAM_ID,
    (SDK as any).ClmmProgramId,
    (SDK as any).PROGRAM_ID?.CLMM,
    (SDK as any).PROGRAM_IDS?.CLMM,
    (SDK as any).PROGRAM_IDS?.CLMM_V2,
    (SDK as any).default?.CLMM_PROGRAM_ID,
  ]
  for (const cand of candidates) {
    try {
      if (cand) return toPublicKey(cand)
    } catch {}
  }
  return new PublicKey('CLMMm7ctS5Xw2qVTL4x1X2LFkW1zD6kH19V7S8hKQ2k')
}

const CLMM_PROGRAM_ID = extractProgramId()

function getPositionPdaFromMint(mint: PublicKey): PublicKey {
  const [addr] = PublicKey.findProgramAddressSync([Buffer.from('position'), mint.toBuffer()], CLMM_PROGRAM_ID)
  return addr
}

async function scanOwnerForNftish(connection: Connection, ownerPk: PublicKey): Promise<string[]> {
  const out: string[] = []
  const programs = [
    tryPublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'),
    tryPublicKey('TokenzQdBNbLqP5dK3W3dH7hJZ8Fj5nV9vWwHES1s6Cw'),
  ].filter(Boolean) as PublicKey[]

  for (const programId of programs) {
    try {
      const resp: any = await connection.getParsedTokenAccountsByOwner(ownerPk, { programId })
      const items = resp?.value || resp?.result?.value || []
      for (const it of items) {
        try {
          const info = it.account?.data?.parsed?.info || it?.data?.parsed?.info
          const amount = new Decimal(String(info?.tokenAmount?.amount ?? '0'))
          const decimals = Number(info?.tokenAmount?.decimals ?? 0)
          const mint = String(info?.mint || '')
          if (decimals === 0 && amount.greaterThan(0) && mint && !out.includes(mint)) {
            out.push(mint)
          }
        } catch {}
      }
    } catch {}
  }
  return out
}

type PositionDecoded = {
  pool: string
  posMint: string
  liquidity: Decimal
  tickLower: number
  tickUpper: number
}

type PoolDecoded = {
  sqrt: Decimal
  mintA: string
  mintB: string
  decA: number
  decB: number
}

const decimalPower = (d: number) => new Decimal(10).pow(d)

const toNumber = (value: any, fallback = 0) => {
  if (typeof value === 'number') return value
  if (typeof value === 'bigint') return Number(value)
  if (typeof value === 'string') {
    const n = Number(value)
    return Number.isFinite(n) ? n : fallback
  }
  if (value && typeof value.toNumber === 'function') {
    try {
      return Number(value.toNumber())
    } catch {}
  }
  return fallback
}

const toDecimal = (value: any) => {
  if (value === undefined || value === null) return new Decimal(0)
  if (Decimal.isDecimal(value)) return value as Decimal
  if (typeof value === 'bigint') return new Decimal(value.toString())
  if (typeof value === 'number') return new Decimal(value)
  if (typeof value === 'string') return new Decimal(value || '0')
  if (value.toString) return new Decimal(value.toString())
  return new Decimal(0)
}

const extractPrice = (value: any): Decimal => {
  if (value === undefined || value === null) return new Decimal(0)
  if (typeof value === 'number' || typeof value === 'string') return new Decimal(value)
  if (typeof value === 'bigint') return new Decimal(value.toString())
  if (value.uiPrice !== undefined) return new Decimal(value.uiPrice)
  if (value.price !== undefined) return new Decimal(value.price)
  if (value.value !== undefined) return new Decimal(value.value)
  if (value.toString) {
    const s = value.toString()
    if (s && s !== '[object Object]') {
      try { return new Decimal(s) } catch {}
    }
  }
  return new Decimal(0)
}

async function main() {
  const connection = new Connection(RPC, 'confirmed')

  let mintStrings = inputMints.slice()
  if (!mintStrings.length && owner) {
    console.log('🔎 No --mints provided; scanning owner token accounts for NFT-like tokens…')
    mintStrings = await scanOwnerForNftish(connection, owner)
  }
  if (!mintStrings.length) {
    console.error('❌ No candidate mints. Pass --mints <M1[,M2,…]> or hold a CL position NFT.')
    process.exit(2)
  }

  const mintPairs = mintStrings
    .map((mintStr) => {
      try {
        const mintPk = new PublicKey(mintStr)
        return { mintStr, mintPk, pda: getPositionPdaFromMint(mintPk) }
      } catch (e) {
        console.warn('   • Skipping invalid mint:', mintStr)
        return null
      }
    })
    .filter(Boolean) as { mintStr: string; mintPk: PublicKey; pda: PublicKey }[]

  if (!mintPairs.length) {
    console.log('   (no valid mints to query)')
    return
  }

  const posInfos = await connection.getMultipleAccountsInfo(mintPairs.map((p) => p.pda), { commitment: 'confirmed' })
  const decoded: PositionDecoded[] = []

  for (let i = 0; i < posInfos.length; i++) {
    const info = posInfos[i]
    if (!info?.data) continue
    try {
      const dec: any = PositionInfoLayout.decode(Buffer.from(info.data as Buffer))
      const poolVal = dec.poolId || dec.pool || dec.poolKey || dec.poolAddress
      const poolPk = poolVal ? toPublicKey(poolVal) : null
      if (!poolPk) continue

      const tickLower = toNumber(
        dec.tickLowerIndex ?? dec.tickLower ?? dec.lowerTick ?? dec.lower ?? dec.tickLowerIdx ?? dec.tickLowerIndexNet,
        0
      )
      const tickUpper = toNumber(
        dec.tickUpperIndex ?? dec.tickUpper ?? dec.upperTick ?? dec.upper ?? dec.tickUpperIdx ?? dec.tickUpperIndexNet,
        0
      )
      const liquidityRaw =
        dec.liquidity !== undefined
          ? dec.liquidity
          : dec.liq !== undefined
          ? dec.liq
          : dec.liquidityAmount !== undefined
          ? dec.liquidityAmount
          : dec.L ?? 0
      const liquidity = toDecimal(liquidityRaw)
      if (!liquidity.isFinite()) continue

      decoded.push({
        pool: poolPk.toBase58(),
        posMint: mintPairs[i].mintPk.toBase58(),
        liquidity,
        tickLower,
        tickUpper,
      })
    } catch (e) {}
  }

  if (!decoded.length) {
    console.log('   (no decodable CLMM positions)')
    return
  }

  const poolPks = Array.from(new Set(decoded.map((d) => d.pool))).map((s) => new PublicKey(s))
  const poolInfos = await connection.getMultipleAccountsInfo(poolPks, { commitment: 'confirmed' })
  const poolMap: Record<string, PoolDecoded> = {}

  for (let i = 0; i < poolInfos.length; i++) {
    const info = poolInfos[i]
    if (!info?.data) continue
    try {
      const dec: any = PoolInfoLayout.decode(Buffer.from(info.data as Buffer))
      const sqrtRaw =
        dec.sqrtPriceX64 ??
        dec.sqrtPrice ??
        dec.sqrt_price_x64 ??
        dec.sqrt_price ??
        dec.sqrtPrice_64 ??
        dec.currentPrice
      const mintAVal = dec.mintA?.mint ?? dec.mintA ?? dec.tokenMintA ?? dec.tokenA?.mint ?? dec.mint_a
      const mintBVal = dec.mintB?.mint ?? dec.mintB ?? dec.tokenMintB ?? dec.tokenB?.mint ?? dec.mint_b
      const mintA = mintAVal ? toPublicKey(mintAVal).toBase58() : ''
      const mintB = mintBVal ? toPublicKey(mintBVal).toBase58() : ''
      if (!mintA || !mintB || sqrtRaw === undefined) continue

      const decA = toNumber(
        dec.mintDecimalsA ?? dec.decimalsA ?? dec.mintA?.decimals ?? dec.tokenMintADecimals ?? dec.tokenA?.decimals,
        0
      )
      const decB = toNumber(
        dec.mintDecimalsB ?? dec.decimalsB ?? dec.mintB?.decimals ?? dec.tokenMintBDecimals ?? dec.tokenB?.decimals,
        0
      )

      poolMap[poolPks[i].toBase58()] = {
        sqrt: q64ToDecimal(sqrtRaw),
        mintA,
        mintB,
        decA,
        decB,
      }
    } catch {}
  }

  if (!Object.keys(poolMap).length) {
    console.log('   (no matching pools for decoded positions)')
    return
  }

  let priceMap: Record<string, Decimal> = {}
  if (priceFetch) {
    try {
      const uniqMints = Array.from(new Set(Object.values(poolMap).flatMap((p) => [p.mintA, p.mintB]))).filter(Boolean)
      let result = await (priceFetch as Function).call(Price, { tokenMints: uniqMints, connection })
      if (!result && uniqMints.length) {
        try {
          result = await (priceFetch as Function).call(Price, connection, uniqMints)
        } catch {}
      }
      priceMap = {}
      if (result instanceof Map) {
        for (const [key, val] of result.entries()) {
          const mint = key instanceof PublicKey ? key.toBase58() : String(key)
          priceMap[mint] = extractPrice(val)
        }
      } else if (Array.isArray(result)) {
        for (const entry of result) {
          if (!entry) continue
          const mint = entry.mint || entry.tokenMint || entry.address || entry.id
          if (!mint) continue
          priceMap[String(mint)] = extractPrice(entry.price ?? entry.uiPrice ?? entry.value ?? entry)
        }
      } else if (result && typeof result === 'object') {
        for (const [key, val] of Object.entries(result)) {
          priceMap[String(key)] = extractPrice(val)
        }
      }
    } catch (e) {
      console.warn('   • Price fetch failed:', (e as Error)?.message ?? e)
    }
  }

  console.log('\n💎 Raydium CL Positions (raw chain decode)\n')
  console.log('Pool'.padEnd(12), 'Position'.padEnd(14), 'TokenA'.padEnd(28), 'TokenB'.padEnd(28), 'USD')

  let total = new Decimal(0)
  for (const row of decoded) {
    const pool = poolMap[row.pool]
    if (!pool) continue

    const sqrtLower = sqrtPriceFromTick(row.tickLower)
    const sqrtUpper = sqrtPriceFromTick(row.tickUpper)
    const { amt0, amt1 } = amountsFromLiquidity(row.liquidity, sqrtLower, pool.sqrt, sqrtUpper)

    const uiA = amt0.div(decimalPower(pool.decA || 0))
    const uiB = amt1.div(decimalPower(pool.decB || 0))

    const pA = priceMap[pool.mintA] ?? new Decimal(0)
    const pB = priceMap[pool.mintB] ?? new Decimal(0)

    const usd = uiA.mul(pA).add(uiB.mul(pB))
    total = total.add(usd)

    const tokenALabel = `${uiA.toSignificantDigits(6)} ${short(pool.mintA)}`.padEnd(28)
    const tokenBLabel = `${uiB.toSignificantDigits(6)} ${short(pool.mintB)}`.padEnd(28)

    console.log(
      short(row.pool).padEnd(12),
      short(row.posMint).padEnd(14),
      tokenALabel,
      tokenBLabel,
      `$${usd.toSignificantDigits(6)}`
    )
  }

  console.log('\nTotal ≈', `$${total.toSignificantDigits(8)}`)
}

main().catch((e) => {
  console.error('❌ Fatal:', (e as Error)?.stack || (e as Error)?.message || e)
  process.exit(1)
})
