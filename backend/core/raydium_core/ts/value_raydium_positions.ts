// @ts-check
import 'dotenv/config'
import { Connection, PublicKey } from '@solana/web3.js'
import Decimal from 'decimal.js'
import {
  CLMM_PROGRAM_ID,
  getPdaPersonalPositionAddress,
  PositionInfoLayout,
  PoolInfoLayout,
  PositionUtils,
  SqrtPriceMath,
} from '@raydium-io/raydium-sdk-v2'
import * as dns from 'node:dns'

// Prefer IPv4 to sidestep Windows/ISP DNS weirdness.
if ((dns as any).setDefaultResultOrder) {
  ;(dns as any).setDefaultResultOrder('ipv4first')
}

const CLMM_ID = new PublicKey(CLMM_PROGRAM_ID)
const RPC = process.env.RPC_URL || process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com'

const argv = process.argv.slice(2)
const arg = (k: string) => {
  const i = argv.indexOf(k)
  return i >= 0 ? argv[i + 1] : undefined
}

const ownerStr = arg('--owner')
const mintsCsv = arg('--mints')
const overridePriceUrl = arg('--price-url') || process.env.JUP_PRICE_URL
const mintList: string[] = (mintsCsv ? mintsCsv.split(',').map(s => s.trim()).filter(Boolean) : [])

const short = (s: string) => (s.length > 12 ? `${s.slice(0, 6)}…${s.slice(-6)}` : s)
function isValidPkStr(s: string) { try { new PublicKey(s); return true } catch { return false } }

async function discoverOwnerMints(conn: Connection, owner: PublicKey) {
  // Scan BOTH legacy SPL Token and Token-2022 for dec=0 balances
  const TOKEN_LEGACY = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
  const TOKEN_2022 = new PublicKey('TokenzQdBNbLqPbwZbzxACjuNbWVHX8sDiiF2CwZJ7')

  async function scan(pid: PublicKey) {
    const resp: any = await (conn as any).getParsedTokenAccountsByOwner(owner, { programId: pid })
    const items = resp?.value || []
    const out: string[] = []
    for (const it of items) {
      const info = it.account?.data?.parsed?.info
      const dec = Number(info?.tokenAmount?.decimals ?? 0)
      const amt = new Decimal(String(info?.tokenAmount?.amount ?? '0'))
      const mint = String(info?.mint ?? '')
      if (dec === 0 && mint && isValidPkStr(mint) && amt.gt(0)) out.push(mint)
    }
    return out
  }

  const [a, b] = await Promise.all([scan(TOKEN_LEGACY), scan(TOKEN_2022)])
  return [...new Set([...a, ...b])]
}

function priceFromSqrt(pool: ReturnType<typeof PoolInfoLayout.decode>) {
  const sqrtPrice = pool.sqrtPriceX64
  const decimalsA = pool.mintDecimalsA
  const decimalsB = pool.mintDecimalsB
  return SqrtPriceMath.sqrtPriceX64ToPrice(sqrtPrice, decimalsA, decimalsB)
}

// ------------ Resilient Jupiter price fetch ------------
type JupV6 = { data?: Record<string, { price?: number }> }
type JupV4 = { data?: Record<string, { price?: number }> }
type JupLiteV3 = Record<string, { usdPrice?: number } | number>

function chunk<T>(arr: T[], size = 60): T[][] {
  const out: T[][] = []
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size))
  return out
}

function sleep(ms: number) { return new Promise(res => setTimeout(res, ms)) }

function withTimeout<T>(p: Promise<T>, ms = 8000): Promise<T> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => reject(new Error(`timeout after ${ms}ms`)), ms)
    p.then(v => { clearTimeout(t); resolve(v) }).catch(e => { clearTimeout(t); reject(e) })
  })
}

async function fetchOne(url: string) {
  const res = await withTimeout(fetch(url, { method: 'GET', headers: { accept: 'application/json' } }), 8000)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

async function fetchJupPrices(mints: string[]): Promise<Record<string, number>> {
  const ids = Array.from(new Set(mints))
  const out: Record<string, number> = {}

  // Priority list; you can override with --price-url or JUP_PRICE_URL
  const bases = (overridePriceUrl ? [overridePriceUrl] : []).concat([
    'https://price.jup.ag/v6/price',   // modern
    'https://price.jup.ag/v4/price',   // older
    'https://lite-api.jup.ag/price/v3' // lite mapping
  ])

  for (const c of chunk(ids, 50)) {
    let ok = false, lastErr: any = null
    for (const base of bases) {
      const url = `${base}${base.includes('?') ? '&' : '?'}ids=${encodeURIComponent(c.join(','))}`
      try {
        const json: any = await fetchOne(url)
        // Unify v6/v4 ({data: {mint: {price}}}) and lite v3 (top-level {mint: {usdPrice}})
        if (json?.data && typeof json.data === 'object') {
          for (const [k, v] of Object.entries(json.data as Record<string, any>)) {
            const p = (v as any).price ?? (v as any).usdPrice
            if (typeof p === 'number' && isFinite(p)) out[k] = p
          }
        } else if (json && typeof json === 'object') {
          for (const [k, v] of Object.entries(json as JupLiteV3)) {
            const p = typeof v === 'number' ? v : (v as any)?.usdPrice ?? (v as any)?.price
            if (typeof p === 'number' && isFinite(p)) out[k] = p
          }
        }
        ok = true
        break
      } catch (e: any) {
        lastErr = e
        // brief backoff before trying next base
        await sleep(150)
      }
    }
    if (!ok) {
      throw new Error(`All Jupiter price endpoints failed for ids=[${c.join(',')}]: ${lastErr?.message || lastErr}`)
    }
  }
  return out
}

// -------------------------------------------------------

;(async () => {
  const conn = new Connection(RPC, 'confirmed')

  let mints = [...new Set(mintList)]
  if (mints.length === 0) {
    if (!ownerStr) {
      console.error('No --mints and no --owner. Supply --mints <M1[,M2…]> or --owner <PUBKEY>.')
      process.exit(2)
    }
    try {
      const owner = new PublicKey(ownerStr)
      mints = await discoverOwnerMints(conn, owner)
      if (!mints.length) {
        console.error('No NFT-like tokens (dec=0) found for owner; pass --mints explicitly.')
        process.exit(2)
      }
    } catch (e) {
      console.error('Owner scan failed; pass --mints. Detail:', (e as any)?.message || e)
      process.exit(1)
    }
  }

  const epochInfo = await conn.getEpochInfo()

  const targets: {
    mint: PublicKey
    posPk: PublicKey
    poolId: PublicKey
    position: ReturnType<typeof PositionInfoLayout.decode>
  }[] = []

  for (const m of mints) {
    let mintPk: PublicKey
    try { mintPk = new PublicKey(m) } catch (e) { continue }

    const { publicKey: posPk } = getPdaPersonalPositionAddress(CLMM_ID, mintPk)
    const posAcc = await conn.getAccountInfo(posPk)
    if (!posAcc?.data) continue

    try {
      const position = PositionInfoLayout.decode(posAcc.data)
      const poolId = new PublicKey(position.poolId)
      targets.push({ mint: mintPk, posPk, poolId, position })
    } catch {}
  }

  if (!targets.length) {
    console.error('No matching CLMM position accounts; nothing to value.')
    process.exit(2)
  }

  // Batch pools
  const poolKeys = [...new Map(targets.map(t => [t.poolId.toBase58(), t.poolId])).values()]
  const poolAccs = await conn.getMultipleAccountsInfo(poolKeys)
  const poolMap = new Map<string, ReturnType<typeof PoolInfoLayout.decode>>()
  poolKeys.forEach((pk, i) => {
    const acc = poolAccs[i]
    if (acc?.data) {
      try { poolMap.set(pk.toBase58(), PoolInfoLayout.decode(acc.data)) } catch {}
    }
  })

  // Prices for both legs across pools
  const priceMintSet = new Set<string>()
  for (const pool of poolMap.values()) {
    priceMintSet.add(pool.mintA.toBase58())
    priceMintSet.add(pool.mintB.toBase58())
  }
  const priceMap = await fetchJupPrices([...priceMintSet])

  const rows: {
    poolPk: string
    posMint: string
    tokenA: string
    tokenB: string
    usd: string
  }[] = []

  for (const t of targets) {
    const pool = poolMap.get(t.poolId.toBase58())
    if (!pool) {
      rows.push({ poolPk: t.poolId.toBase58(), posMint: t.mint.toBase58(), tokenA: '-', tokenB: '-', usd: '-' })
      continue
    }

    // Raydium SDK math
    const poolPrice = priceFromSqrt(pool)
    const poolInfoForMath = {
      price: poolPrice.toString(),
      mintA: { decimals: pool.mintDecimalsA, extensions: {} },
      mintB: { decimals: pool.mintDecimalsB, extensions: {} },
    } as any

    let amountAUi: Decimal | null = null
    let amountBUi: Decimal | null = null
    let usdValue: Decimal | null = null

    try {
      const amounts = PositionUtils.getAmountsFromLiquidity({
        poolInfo: poolInfoForMath,
        ownerPosition: t.position as any,
        liquidity: t.position.liquidity,
        slippage: 0,
        add: false,
        epochInfo,
      })
      const rawA = amounts.amountA.amount
      const rawB = amounts.amountB.amount
      amountAUi = new Decimal(rawA.toString()).div(new Decimal(10).pow(pool.mintDecimalsA))
      amountBUi = new Decimal(rawB.toString()).div(new Decimal(10).pow(pool.mintDecimalsB))
    } catch (e) {
      // keep placeholders
    }

    const mintA = pool.mintA.toBase58()
    const mintB = pool.mintB.toBase58()
    const pA = priceMap[mintA]
    const pB = priceMap[mintB]

    if (amountAUi && amountBUi && (typeof pA === 'number' || typeof pB === 'number')) {
      const usdA = typeof pA === 'number' ? amountAUi.mul(pA) : new Decimal(0)
      const usdB = typeof pB === 'number' ? amountBUi.mul(pB) : new Decimal(0)
      usdValue = usdA.add(usdB)
    }

    rows.push({
      poolPk: t.poolId.toBase58(),
      posMint: t.mint.toBase58(),
      tokenA: amountAUi ? `${amountAUi.toSignificantDigits(6).toString()} ${short(mintA)}` : `- ${short(mintA)}`,
      tokenB: amountBUi ? `${amountBUi.toSignificantDigits(6).toString()} ${short(mintB)}` : `- ${short(mintB)}`,
      usd: usdValue ? `$${usdValue.toSignificantDigits(6).toString()}` : '-',
    })
  }

  console.log('\n💎 Raydium CL Positions — USD value (SDK + Jupiter)\n')
  console.log('Pool'.padEnd(44), 'Position'.padEnd(14), 'TokenA'.padEnd(22), 'TokenB'.padEnd(22), 'USD')
  for (const r of rows) {
    console.log(
      short(r.poolPk).padEnd(12),
      short(r.posMint).padEnd(14),
      String(r.tokenA).padEnd(22),
      String(r.tokenB).padEnd(22),
      r.usd ?? '-',
    )
  }
})()
