// @ts-nocheck
import 'dotenv/config'
import { Connection, PublicKey } from '@solana/web3.js'
import Decimal from 'decimal.js'

// Load Raydium SDK — prefer v2, fall back to v1
let SDK: any = {}
try {
  SDK = require('@raydium-io/raydium-sdk-v2')
} catch {
  try {
    SDK = require('@raydium-io/raydium-sdk')
  } catch (e) {
    console.error('❌ Could not load @raydium-io/raydium-sdk[-v2]. Install one of them.')
    process.exit(2)
  }
}
const { Raydium } = SDK
const Clmm = SDK.Clmm || SDK.CLMM || SDK.ClmmPool || SDK.clmm || {}
const Price = SDK.Price || SDK.price || {}
const fetchMultipleMintInfos =
  SDK.fetchMultipleMintInfos ||
  SDK.MintUtil?.fetchMultipleMintInfos ||
  SDK.Token?.fetchMultipleMintInfos

const RPC =
  process.env.RPC_URL || process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com'

const args = process.argv.slice(2)
function argVal(flag: string): string | undefined {
  const i = args.indexOf(flag)
  return i >= 0 ? args[i + 1] : undefined
}
const ownerStr = argVal('--owner')
const mintListStr = argVal('--mints') // comma-separated optional

if (!ownerStr && !mintListStr) {
  console.error('Usage:')
  console.error('  ts-node value_raydium_positions.ts --owner <PUBKEY>')
  console.error('  ts-node value_raydium_positions.ts --mints <MINT1,MINT2,...>')
  process.exit(2)
}

const owner = ownerStr ? new PublicKey(ownerStr) : undefined
const inputMints = mintListStr
  ? mintListStr
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  : []

const short = (s: string) => `${s.slice(0, 6)}…${s.slice(-6)}`

function pick<T extends object>(obj: T, names: string[]): { name?: string; fn?: any } {
  for (const n of names) {
    if (obj && typeof (obj as any)[n] === 'function') return { name: n, fn: (obj as any)[n].bind(obj) }
  }
  return {}
}

async function main() {
  const connection = new Connection(RPC, 'confirmed')
  const ray = await Raydium.load?.({ connection })
  if (!ray) {
    console.error('❌ Raydium SDK did not load a client. Keys on SDK:', Object.keys(SDK))
    process.exit(2)
  }

  // Discover CLMM methods present in this SDK
  const mFetchPositionsByOwner = pick(Clmm, [
    'fetchPositionsByOwner',
    'fetchPositionsByUser',
    'getPositionsByOwner',
    'getPositionsByUser',
  ])
  const mFetchPosInfos = pick(Clmm, [
    'fetchPositionInfos',
    'fetchPositionsInfo',
    'getPositionInfos',
    'getPositionsInfo',
    'getPositionsByMints',
  ])
  const mFetchPools = pick(Clmm, [
    'fetchMultiplePoolInfos',
    'fetchPools',
    'getMultiplePoolInfos',
    'getPools',
  ])
  const mAmountsFromLiq = pick(Clmm, [
    'getAmountsFromLiquidity',
    'liquidityToTokenAmounts',
    'getTokenAmountsFromLiquidity',
  ])
  const mPriceMulti = pick(Price, ['fetchMultiple', 'getMultiple', 'getPrices'])

  const have = {
    Clmm: Object.keys(Clmm || {}),
    Price: Object.keys(Price || {}),
    fetchMultipleMintInfos: !!fetchMultipleMintInfos,
    methods: {
      byOwner: mFetchPositionsByOwner.name,
      posInfos: mFetchPosInfos.name,
      pools: mFetchPools.name,
      amounts: mAmountsFromLiq.name,
      priceMulti: mPriceMulti.name,
    },
  }

  // Diagnostics so you can see what exists in your install
  console.log('🔧 SDK check →', JSON.stringify(have.methods), '\n')

  // 1) Build the list of position mints we’ll value
  let positionMints: PublicKey[] = []

  if (inputMints.length > 0) {
    positionMints = inputMints.map((m) => new PublicKey(m))
  } else if (owner && mFetchPositionsByOwner.fn) {
    const briefs = await mFetchPositionsByOwner.fn({ connection, owner })
    if (!briefs?.length) {
      console.log('   (no Raydium CLMM positions found for owner)')
      return
    }
    positionMints = briefs.map((b: any) => b.positionNftMint ?? b.mint ?? b.nftMint).map((x: any) => new PublicKey(x))
  } else {
    console.error('❌ No --mints provided and this SDK lacks a positions-by-owner method.')
    console.error('   Pass NFT mints via:  --mints MINT1,MINT2,...  (from Python option 2 output)')
    process.exit(2)
  }

  // 2) Fetch position infos
  if (!mFetchPosInfos.fn) {
    console.error('❌ SDK missing a "fetch position infos" function:', have.methods.posInfos)
    console.error('   Available Clmm keys:', have.Clmm.slice(0, 40).join(', '), '…')
    process.exit(2)
  }
  const posInfos = await mFetchPosInfos.fn({ connection, positions: positionMints })
  if (!posInfos?.length) {
    console.log('   (no position infos returned)')
    return
  }

  // 3) Get pool ids from positions and fetch pools
  const poolIds = Array.from(
    new Set(
      posInfos
        .map((p: any) => p.poolId ?? p.pool?.id)
        .filter(Boolean)
        .map((x: any) => (typeof x === 'string' ? x : x.toBase58())),
    ),
  ).map((s) => new PublicKey(s))

  if (!mFetchPools.fn) {
    console.error('❌ SDK missing a "fetch pools" function:', have.methods.pools)
    console.error('   Available Clmm keys:', have.Clmm.slice(0, 40).join(', '), '…')
    process.exit(2)
  }
  const pools = await mFetchPools.fn({ connection, poolIds })

  // 4) Collect mints for pricing/decimals
  const mintSet = new Set<string>()
  for (const p of pools) {
    const a = p.mintA?.mint?.toBase58?.() ?? String(p.mintA?.mint ?? '')
    const b = p.mintB?.mint?.toBase58?.() ?? String(p.mintB?.mint ?? '')
    if (a) mintSet.add(a)
    if (b) mintSet.add(b)
  }

  if (!fetchMultipleMintInfos) {
    console.error('❌ SDK missing fetchMultipleMintInfos; cannot compute UI amounts safely.')
    process.exit(2)
  }
  const mintInfos = await fetchMultipleMintInfos({
    connection,
    mints: Array.from(mintSet).map((m) => new PublicKey(m)),
  })

  // Pricing (best effort)
  let priceMap: Record<string, number> = {}
  if (mPriceMulti.fn) {
    priceMap = (await mPriceMulti.fn({ tokenMints: Array.from(mintSet), connection, raydium: ray })) || {}
  }

  if (!mAmountsFromLiq.fn) {
    console.error('❌ SDK missing a liquidity→amounts function:', have.methods.amounts)
    console.error('   Available Clmm keys:', have.Clmm.slice(0, 40).join(', '), '…')
    process.exit(2)
  }

  // Map pools by id for quick lookup
  const poolById = new Map<string, any>()
  for (const p of pools) {
    const id = p.id?.toBase58?.() ?? String(p.id)
    poolById.set(id, p)
  }

  let total = new Decimal(0)
  console.log('\n💎 Raydium CL Positions\n')
  console.log('Pool'.padEnd(12), 'Position'.padEnd(14), 'TokenA'.padEnd(22), 'TokenB'.padEnd(22), 'USD')

  for (const pos of posInfos) {
    const poolId = pos.poolId?.toBase58?.() ?? String(pos.poolId)
    const pool = poolById.get(poolId)
    if (!pool) continue

    const res = await mAmountsFromLiq.fn({
      poolInfo: pool,
      tickLower: pos.tickLower ?? pos.lowerTick,
      tickUpper: pos.tickUpper ?? pos.upperTick,
      liquidity: pos.liquidity,
    })

    const amountA = res.amountA ?? res.tokenAmountA ?? res.a ?? 0
    const amountB = res.amountB ?? res.tokenAmountB ?? res.b ?? 0

    const mintA = pool.mintA?.mint?.toBase58?.() ?? String(pool.mintA?.mint)
    const mintB = pool.mintB?.mint?.toBase58?.() ?? String(pool.mintB?.mint)
    const decA = mintInfos[mintA]?.decimals ?? 0
    const decB = mintInfos[mintB]?.decimals ?? 0

    const uiA = new Decimal(String(amountA)).div(new Decimal(10).pow(decA))
    const uiB = new Decimal(String(amountB)).div(new Decimal(10).pow(decB))

    const pA = new Decimal(priceMap[mintA] ?? 0)
    const pB = new Decimal(priceMap[mintB] ?? 0)
    const usd = uiA.mul(pA).add(uiB.mul(pB))
    total = total.add(usd)

    const symA = pool.mintA?.symbol ?? short(mintA)
    const symB = pool.mintB?.symbol ?? short(mintB)
    const posMint = pos.positionNftMint?.toBase58?.() ?? String(pos.positionNftMint)
    console.log(
      short(poolId).padEnd(12),
      short(posMint).padEnd(14),
      `${uiA.toSignificantDigits(6).toString()} ${symA}`.padEnd(22),
      `${uiB.toSignificantDigits(6).toString()} ${symB}`.padEnd(22),
      `$${usd.toSignificantDigits(6).toString()}`,
    )
  }

  console.log('\nTotal ≈', `$${total.toSignificantDigits(8).toString()}`)
}

main().catch((e) => {
  console.error('Fatal:', e)
  process.exit(1)
})
