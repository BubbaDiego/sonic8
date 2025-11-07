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

const CLMM_ID = new PublicKey(CLMM_PROGRAM_ID)
const RPC = process.env.RPC_URL || process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com'

const argv = process.argv.slice(2)
const arg = (k: string) => {
  const i = argv.indexOf(k)
  return i >= 0 ? argv[i + 1] : undefined
}
const ownerStr = arg('--owner')
const mintsCsv = arg('--mints')
const mintList: string[] = (mintsCsv ? mintsCsv.split(',').map(s => s.trim()).filter(Boolean) : [])

const short = (s: string) => (s.length > 12 ? `${s.slice(0, 6)}…${s.slice(-6)}` : s)

function isValidPkStr(s: string) {
  try { new PublicKey(s); return true } catch { return false }
}

async function discoverOwnerMints(conn: Connection, owner: PublicKey) {
  // Token Program v1 (legacy) + Token-2022: you already scan those in Python,
  // but for standalone TS use, scan the legacy Program here for dec=0 balances.
  const TOKEN_LEGACY = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
  const resp: any = await (conn as any).getParsedTokenAccountsByOwner(owner, { programId: TOKEN_LEGACY })
  const items = resp?.value || []
  const found: string[] = []
  for (const it of items) {
    const info = it.account?.data?.parsed?.info
    const dec = Number(info?.tokenAmount?.decimals || 0)
    const amt = new Decimal(String(info?.tokenAmount?.amount || '0'))
    const mint = String(info?.mint || '')
    if (dec === 0 && mint && isValidPkStr(mint) && amt.gt(0)) found.push(mint)
  }
  return [...new Set(found)]
}

function priceFromSqrt(pool: ReturnType<typeof PoolInfoLayout.decode>) {
  const sqrtPrice = pool.sqrtPriceX64
  const decimalsA = pool.mintDecimalsA
  const decimalsB = pool.mintDecimalsB
  return SqrtPriceMath.sqrtPriceX64ToPrice(sqrtPrice, decimalsA, decimalsB)
}

// --- Jupiter v6 price fetch (mints) ---
type JupV6 = { data?: Record<string, { price?: number }> }
function chunk<T>(arr: T[], size = 60): T[][] {
  const out: T[][] = []
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size))
  return out
}
async function fetchJupPrices(mints: string[]): Promise<Record<string, number>> {
  const ids = Array.from(new Set(mints))
  const out: Record<string, number> = {}
  for (const c of chunk(ids, 60)) {
    const url = `https://price.jup.ag/v6/price?ids=${encodeURIComponent(c.join(','))}`
    const res = await fetch(url, { method: 'GET' })
    if (!res.ok) continue
    const json = (await res.json()) as JupV6
    for (const [k, v] of Object.entries(json?.data || {})) {
      if (typeof v?.price === 'number' && isFinite(v.price)) out[k] = v.price
    }
  }
  return out
}

;(async () => {
  const conn = new Connection(RPC, 'confirmed')

  let mints = [...new Set(mintList)]
  if (mints.length === 0) {
    if (!ownerStr) {
      console.error('No --mints provided and no --owner to scan; supply --mints <M1[,M2…]>.')
      process.exit(2)
    }
    try {
      const owner = new PublicKey(ownerStr)
      mints = await discoverOwnerMints(conn, owner)
      if (!mints.length) {
        console.error('No NFT-like tokens found for owner; pass --mints <M1[,M2…]>.')
        process.exit(2)
      }
    } catch (e) {
      console.error('Owner scan failed, pass --mints explicitly. Detail:', (e as any)?.message || e)
      process.exit(1)
    }
  }

  const epochInfo = await conn.getEpochInfo()

  // Resolve CLMM position accounts for each NFT mint
  const targets: {
    mint: PublicKey
    posPk: PublicKey
    poolId: PublicKey
    position: ReturnType<typeof PositionInfoLayout.decode>
  }[] = []

  for (const m of mints) {
    let mintPk: PublicKey
    try { mintPk = new PublicKey(m) } catch (e) {
      console.error('Invalid mint', m, '-', (e as any)?.message || e)
      continue
    }

    const { publicKey: posPk } = getPdaPersonalPositionAddress(CLMM_ID, mintPk)
    const posAcc = await conn.getAccountInfo(posPk)
    if (!posAcc?.data) {
      // Not a CLMM position; skip silently so the console stays friendly.
      continue
    }
    let pos
    try { pos = PositionInfoLayout.decode(posAcc.data) } catch (e) {
      console.error('Failed to decode position for mint', m, '-', (e as any)?.message || e)
      continue
    }
    const poolId = new PublicKey(pos.poolId)
    targets.push({ mint: mintPk, posPk, poolId, position: pos })
  }

  if (!targets.length) {
    console.error('No matching CLMM position accounts; cannot value.')
    process.exit(2)
  }

  // Batch-fetch and decode all pools
  const uniquePoolKeys = [...new Map(targets.map(t => [t.poolId.toBase58(), t.poolId])).values()]
  const poolAccounts = await conn.getMultipleAccountsInfo(uniquePoolKeys)
  const poolMap = new Map<string, ReturnType<typeof PoolInfoLayout.decode>>()
  uniquePoolKeys.forEach((pk, idx) => {
    const acc = poolAccounts[idx]
    if (acc?.data) {
      try { poolMap.set(pk.toBase58(), PoolInfoLayout.decode(acc.data)) }
      catch (e) { /* ignore */ }
    }
  })

  // Build a mint set for pricing
  const priceMintSet = new Set<string>()
  for (const pool of poolMap.values()) {
    priceMintSet.add(pool.mintA.toBase58())
    priceMintSet.add(pool.mintB.toBase58())
  }
  const priceMap = await fetchJupPrices([...priceMintSet])  // Jupiter v6

  const rows: {
    poolPk: string
    posMint: string
    tokenA: string
    tokenB: string
    usd: string
  }[] = []

  for (const target of targets) {
    const poolIdStr = target.poolId.toBase58()
    const pool = poolMap.get(poolIdStr)
    if (!pool) {
      rows.push({ poolPk: poolIdStr, posMint: target.mint.toBase58(), tokenA: '-', tokenB: '-', usd: '-' })
      continue
    }

    // Use Raydium math to compute UI amounts
    const poolPrice = priceFromSqrt(pool)  // unused for USD now but handy for debugging
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
        ownerPosition: target.position as any,
        liquidity: target.position.liquidity,
        slippage: 0,
        add: false,
        epochInfo,
      })
      const rawA = amounts.amountA.amount
      const rawB = amounts.amountB.amount
      amountAUi = new Decimal(rawA.toString()).div(new Decimal(10).pow(pool.mintDecimalsA))
      amountBUi = new Decimal(rawB.toString()).div(new Decimal(10).pow(pool.mintDecimalsB))
    } catch (e) {
      console.error('Failed to compute liquidity amounts for position', target.mint.toBase58(), '-', (e as any)?.message || e)
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
      poolPk: poolIdStr,
      posMint: target.mint.toBase58(),
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
