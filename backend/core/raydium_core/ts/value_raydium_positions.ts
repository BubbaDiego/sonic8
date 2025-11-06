// @ts-check
import 'dotenv/config'
import { Buffer } from 'buffer'
import { Connection, PublicKey } from '@solana/web3.js'
import Decimal from 'decimal.js'

// Optional: import SDK only to read CLMM program id or prices
let SDK: any = {}
try { SDK = require('@raydium-io/raydium-sdk-v2') } catch {}
if (!Object.keys(SDK).length) {
  try { SDK = require('@raydium-io/raydium-sdk') } catch {}
}

const clmmFromEnv = process.env.CLMM_PROGRAM_ID?.trim()
const CLMM_PROGRAM_ID = (() => {
  try {
    if (clmmFromEnv) return new PublicKey(clmmFromEnv)
  } catch {}
  try {
    if (SDK?.CLMM_PROGRAM_ID) return new PublicKey(SDK.CLMM_PROGRAM_ID)
  } catch {}
  return null
})()

if (!CLMM_PROGRAM_ID) {
  console.error('❌ No CLMM program id found in @raydium-io/* package. Set env CLMM_PROGRAM_ID or install a Raydium SDK.')
  process.exit(2)
}

// Optional price helper if SDK exposes it
const Price = (SDK as any)?.price || (SDK as any)?.Price || null
const fetchPrices = Price && (Price.fetchMultiple || Price.getMultiple || Price.getPrices || null)

const RPC = process.env.RPC_BE ?? process.env.RPC_URL ?? process.env.SOLANA_RPC_URL ?? 'https://api.mainnet-beta.solana.com'

const args = process.argv.slice(2)
const arg = (k: string) => {
  const i = args.indexOf(k)
  return i >= 0 ? args[i + 1] : undefined
}

const ownerStr = arg('--owner')
const mintsCsv = arg('--mints')
const mintList = (mintsCsv ? mintsCsv.split(',').map(s => s.trim()).filter(Boolean) : []) as string[]

const Q64 = new Decimal(2).pow(64)
const sqrtFromTick = (t: number) => new Decimal('1.0001').pow(t)
const short = (s: string) => (s.length > 12 ? `${s.slice(0, 6)}…${s.slice(-6)}` : s)

async function detectMintDecimals(conn: Connection, mintSet: Set<string>) {
  const arr = Array.from(mintSet)
  if (!arr.length) return new Map<string, number>()
  const pubkeys = arr.map(m => new PublicKey(m))
  const infos = await conn.getMultipleAccountsInfo(pubkeys, { commitment: 'confirmed' })
  const out = new Map<string, number>()
  infos.forEach((acc, idx) => {
    const mint = arr[idx]
    if (!acc?.data) return
    const data = acc.data as Buffer
    if (data.length < 45) return
    const view = new DataView(data.buffer, data.byteOffset, data.byteLength)
    out.set(mint, view.getUint8(44))
  })
  return out
}

async function maybeFetchPrices(conn: Connection, mintSet: Set<string>): Promise<Record<string, number>> {
  if (!fetchPrices) return {}
  const tokens = Array.from(mintSet)
  if (!tokens.length) return {}
  try {
    const fn = fetchPrices
    const maybe = fn.length >= 2
      ? await fn.call(Price, tokens, conn)
      : await fn.call(Price, { tokenMints: tokens, connection: conn })
    if (!maybe) return {}
    if (Array.isArray(maybe)) {
      const rec: Record<string, number> = {}
      for (const it of maybe) {
        const mint = typeof it?.mint === 'string' ? it.mint : it?.tokenMint
        const price = typeof it?.price === 'number' ? it.price : Number(it?.value ?? 0)
        if (mint && Number.isFinite(price)) rec[mint] = price
      }
      return rec
    }
    if (typeof maybe === 'object') {
      const rec: Record<string, number> = {}
      for (const [mint, price] of Object.entries(maybe)) {
        if (typeof price === 'number') rec[mint] = price
        else if (price && typeof (price as any).price === 'number') rec[mint] = (price as any).price
      }
      return rec
    }
  } catch {}
  return {}
}

async function main() {
  const conn = new Connection(RPC, 'confirmed')

  let mints = [...new Set(mintList)]
  if (!mints.length && ownerStr) {
    const owner = new PublicKey(ownerStr)
    const TOKEN_2018 = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
    const resp = await conn.getParsedTokenAccountsByOwner(owner, { programId: TOKEN_2018 })
    for (const it of resp.value || []) {
      const info = (it.account as any)?.data?.parsed?.info
      const mint = String(info?.mint ?? '')
      const dec = Number(info?.tokenAmount?.decimals ?? 0)
      const amt = new Decimal(String(info?.tokenAmount?.amount ?? '0'))
      if (dec === 0 && mint && amt.gt(0)) mints.push(mint)
    }
    mints = [...new Set(mints)]
    if (!mints.length) {
      console.error('No NFT-like token mints found for owner; pass --mints <M1[,M2…]>')
      process.exit(2)
    }
  }

  const uniqueWanted = Array.from(new Set(mints))
  const wantedBuffers = uniqueWanted.map(m => ({ mint: m, buf: Buffer.from(new PublicKey(m).toBytes()) }))
  const wantedSet = new Set(uniqueWanted.map(m => new PublicKey(m).toBase58()))

  const programAccs = await conn.getProgramAccounts(CLMM_PROGRAM_ID, { commitment: 'confirmed' })
  const positions: { posPk: PublicKey; data: Buffer }[] = []
  for (const { pubkey, account } of programAccs) {
    const data = account.data as Buffer
    if (!data || data.length < 96) continue
    for (const { buf } of wantedBuffers) {
      if (data.includes(buf)) {
        positions.push({ posPk: pubkey, data })
        break
      }
    }
  }

  if (!positions.length) {
    console.error('No CLMM position accounts found containing provided mint(s).')
    process.exit(2)
  }

  type ParsedPos = { posPk: PublicKey; poolPk: PublicKey; mint: string; liquidity: Decimal; tickL: number; tickU: number }
  const parsed: ParsedPos[] = []
  for (const { posPk, data } of positions) {
    try {
      if (data.length < 89) continue
      const view = new DataView(data.buffer, data.byteOffset, data.byteLength)
      const ownerA = new PublicKey(data.subarray(1, 33))
      const poolA = new PublicKey(data.subarray(33, 65))
      const tickLA = view.getInt32(65, true)
      const tickUA = view.getInt32(69, true)
      const liLoA = view.getBigUint64(73, true)
      const liHiA = view.getBigUint64(81, true)
      const liquidityA = new Decimal(liHiA.toString()).times(Q64).add(new Decimal(liLoA.toString()))

      const mintB = new PublicKey(data.subarray(1, 33))
      const poolB = new PublicKey(data.subarray(33, 65))
      const tickLB = tickLA
      const tickUB = tickUA
      const liquidityB = liquidityA

      let picked: 'A' | 'B' | null = null
      if (wantedSet.has(ownerA.toBase58())) picked = 'A'
      if (wantedSet.has(mintB.toBase58())) picked = 'B'

      if (picked === 'A') {
        parsed.push({ posPk, poolPk: poolA, mint: ownerA.toBase58(), liquidity: liquidityA, tickL: tickLA, tickU: tickUA })
      } else if (picked === 'B') {
        parsed.push({ posPk, poolPk: poolB, mint: mintB.toBase58(), liquidity: liquidityB, tickL: tickLB, tickU: tickUB })
      }
    } catch {}
  }

  if (!parsed.length) {
    console.error('Found position accounts but could not parse fields for provided mint(s).')
    process.exit(2)
  }

  const poolKeys = Array.from(new Set(parsed.map(p => p.poolPk.toBase58()))).map(s => new PublicKey(s))
  const poolInfos = await conn.getMultipleAccountsInfo(poolKeys, { commitment: 'confirmed' })
  const poolMap = new Map<string, { mintA: string; mintB: string; sqrtPrice: Decimal; decA: number; decB: number }>()
  poolInfos.forEach((acc, idx) => {
    const poolPk = poolKeys[idx].toBase58()
    if (!acc?.data) return
    const bytes = acc.data as Buffer
    if (bytes.length < 176) return
    try {
      const mintA = new PublicKey(bytes.subarray(64, 96)).toBase58()
      const mintB = new PublicKey(bytes.subarray(96, 128)).toBase58()
      const sqrtLo = bytes.readBigUInt64LE(160)
      const sqrtHi = bytes.readBigUInt64LE(168)
      const sqrtPrice = new Decimal(sqrtHi.toString()).times(Q64).add(new Decimal(sqrtLo.toString()))
      poolMap.set(poolPk, { mintA, mintB, sqrtPrice, decA: 0, decB: 0 })
    } catch {}
  })

  if (!poolMap.size) {
    console.error('Unable to decode pools for located positions.')
    process.exit(2)
  }

  const mintSet = new Set<string>()
  for (const { mintA, mintB } of poolMap.values()) {
    if (mintA) mintSet.add(mintA)
    if (mintB) mintSet.add(mintB)
  }

  const decimals = await detectMintDecimals(conn, mintSet)
  for (const [key, pool] of poolMap.entries()) {
    pool.decA = decimals.get(pool.mintA) ?? 0
    pool.decB = decimals.get(pool.mintB) ?? 0
    poolMap.set(key, pool)
  }

  const priceMap = await maybeFetchPrices(conn, mintSet)

  console.log('\n💎 Raydium CL Positions (raw decode)\n')
  console.log('Pool'.padEnd(12), 'Position'.padEnd(14), 'TokenA'.padEnd(22), 'TokenB'.padEnd(22), 'USD')

  let total = new Decimal(0)
  for (const pos of parsed) {
    const pool = poolMap.get(pos.poolPk.toBase58())
    if (!pool) continue
    const sqrtL = sqrtFromTick(pos.tickL)
    const sqrtU = sqrtFromTick(pos.tickU)
    const current = pool.sqrtPrice.div(Q64)

    let amountA = new Decimal(0)
    let amountB = new Decimal(0)
    if (current.lte(sqrtL)) {
      amountA = pos.liquidity.times(sqrtU.minus(sqrtL)).div(sqrtL.times(sqrtU))
    } else if (current.gte(sqrtU)) {
      amountB = pos.liquidity.times(sqrtU.minus(sqrtL))
    } else {
      amountA = pos.liquidity.times(sqrtU.minus(current)).div(current.times(sqrtU))
      amountB = pos.liquidity.times(current.minus(sqrtL))
    }

    const uiA = amountA.div(new Decimal(10).pow(pool.decA))
    const uiB = amountB.div(new Decimal(10).pow(pool.decB))
    const priceA = new Decimal(String(priceMap[pool.mintA] ?? 0))
    const priceB = new Decimal(String(priceMap[pool.mintB] ?? 0))
    const usd = uiA.times(priceA).add(uiB.times(priceB))

    console.log(
      short(pos.poolPk.toBase58()).padEnd(12),
      short(pos.mint).padEnd(14),
      `${uiA.toSignificantDigits(6).toString()} ${short(pool.mintA)}`.padEnd(22),
      `${uiB.toSignificantDigits(6).toString()} ${short(pool.mintB)}`.padEnd(22),
      `$${usd.toSignificantDigits(6).toString()}`
    )
    total = total.add(usd)
  }

  console.log('\nTotal ≈', `$${total.toSignificantDigits(8).toString()}`)
}

main().catch(err => {
  console.error('Fatal:', err?.message ?? err)
  process.exit(1)
})
