// @ts-nocheck
import 'dotenv/config'
import { Connection, PublicKey } from '@solana/web3.js'
import Decimal from 'decimal.js'

// Load Raydium SDK (v2 preferred, fallback v1)
let SDK: any = {}
try { SDK = require('@raydium-io/raydium-sdk-v2') } catch {}
if (!SDK || !Object.keys(SDK).length) { try { SDK = require('@raydium-io/raydium-sdk') } catch {} }
if (!SDK || !Object.keys(SDK).length) {
  console.error('❌ Could not load @raydium-io/raydium-sdk[-v2]. Install one of them in ./ts folder.')
  process.exit(2)
}

const RPC = process.env.RPC_URL || process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com'
const args = process.argv.slice(2)
const arg = (f: string) => { const i = args.indexOf(f); return i >= 0 ? args[i+1] : undefined }
const ownerStr = arg('--owner')
const mintsCsv = arg('--mints')
const owner = ownerStr ? new PublicKey(ownerStr) : undefined
const inputMints = (mintsCsv ? mintsCsv.split(',').map(s=>s.trim()).filter(Boolean) : []) as string[]
const short = (s: string) => `${s.slice(0, 6)}…${s.slice(-6)}`

// deep getter for dotted path
const getDeep = (obj: any, path: string) => path.split('.').reduce((a,k)=> (a && k in a) ? a[k] : undefined, obj)
const bindIfFn = (ctx: any, fn: any) => (typeof fn === 'function' ? fn.bind(ctx) : undefined)

async function main() {
  const connection = new Connection(RPC, 'confirmed')

  // Raydium client
  const Raydium = SDK.Raydium || getDeep(SDK, 'default.Raydium') || SDK.raydium
  if (!Raydium) { console.error('❌ Raydium class not found. Keys:', Object.keys(SDK)); process.exit(2) }
  const ray = await (Raydium.load ? Raydium.load({ connection }) : Raydium({ connection }))
  if (!ray) { console.error('❌ Raydium client failed to load.'); process.exit(2) }

  // CLMM namespace OR factory
  const ClmmExport = SDK.Clmm || SDK.CLMM || SDK.clmm || getDeep(SDK, 'default.Clmm') || getDeep(SDK, 'default.CLMM')
  const isFactory = typeof ClmmExport === 'function'
  let ClmmObj: any = ClmmExport

  // If it's a function/factory, call it to get an instance that holds methods.
  if (isFactory) {
    // try common factory signatures
    try {
      ClmmObj = await ClmmExport({ connection })
    } catch {
      try { ClmmObj = await (ClmmExport.load ? ClmmExport.load({ connection }) : ClmmExport({ connection })) } catch {}
    }
  }

  const rootKeys = Object.keys(SDK)
  const clmmKeys = ClmmObj && typeof ClmmObj === 'object' ? Object.keys(ClmmObj) : []
  console.log('🔧 SDK check →', JSON.stringify({ rootKeys, clmmType: typeof ClmmExport, clmmInstanceKeys: clmmKeys }, null, 2), '\n')

  // Try to pick methods first from instance (preferred), then from static export as fallback
  function pickFrom(target: any, names: string[]) {
    for (const n of names) {
      const v = target && (target[n] ?? getDeep(target, n))
      if (typeof v === 'function') return v.bind(target)
    }
    return undefined
  }

  // Position-by-owner (optional)
  const fetchPositionsByOwner =
    pickFrom(ClmmObj, ['fetchPositionsByOwner','fetchPositionsByUser','getPositionsByOwner','getPositionsByUser']) ||
    pickFrom(ClmmExport, ['fetchPositionsByOwner','fetchPositionsByUser','getPositionsByOwner','getPositionsByUser'])

  // Position infos (required)
  const fetchPositionInfos =
    pickFrom(ClmmObj, ['fetchPositionInfos','fetchPositionsInfo','getPositionInfos','getPositionsInfo','getPositionsByMints','fetchPositionsByMints']) ||
    pickFrom(ClmmExport, ['fetchPositionInfos','fetchPositionsInfo','getPositionInfos','getPositionsInfo','getPositionsByMints','fetchPositionsByMints'])

  // Pools (required)
  const fetchPools =
    pickFrom(ClmmObj, ['fetchMultiplePoolInfos','fetchPools','getMultiplePoolInfos','getPools']) ||
    pickFrom(ClmmExport, ['fetchMultiplePoolInfos','fetchPools','getMultiplePoolInfos','getPools'])

  // Liquidity → amounts (required)
  const amountsFromLiquidity =
    pickFrom(ClmmObj, ['getAmountsFromLiquidity','liquidityToTokenAmounts','getTokenAmountsFromLiquidity']) ||
    pickFrom(ClmmExport, ['getAmountsFromLiquidity','liquidityToTokenAmounts','getTokenAmountsFromLiquidity'])

  // Mint infos & pricing
  const fetchMultipleMintInfos =
    SDK.fetchMultipleMintInfos || getDeep(SDK,'MintUtil.fetchMultipleMintInfos') || getDeep(SDK,'Token.fetchMultipleMintInfos') || getDeep(SDK,'default.fetchMultipleMintInfos')
  const Price = SDK.Price || SDK.price || {}
  const priceMultiple = bindIfFn(Price, Price.fetchMultiple || Price.getMultiple || Price.getPrices)

  // Build list of position mints
  let positionMints: PublicKey[] = []
  if (inputMints.length) {
    try { positionMints = inputMints.map((m)=> new PublicKey(m)) } catch (e) {
      console.error('❌ Invalid mint in --mints:', e); process.exit(2)
    }
  } else if (owner && fetchPositionsByOwner) {
    const briefs = await fetchPositionsByOwner({ connection, owner })
    if (!briefs?.length) { console.log('   (no positions for owner)'); return }
    positionMints = briefs.map((b:any)=> new PublicKey(b.positionNftMint ?? b.mint ?? b.nftMint))
  } else {
    console.error('❌ No --mints and this SDK lacks a positions-by-owner method.')
    console.error('   clmmInstanceKeys:', clmmKeys)
    process.exit(2)
  }

  if (!fetchPositionInfos) {
    console.error('❌ SDK missing a "fetch position infos" function.')
    console.error('   clmmInstanceKeys:', clmmKeys)
    process.exit(2)
  }
  const posInfos = await fetchPositionInfos({ connection, positions: positionMints })
  if (!posInfos?.length) { console.log('   (no position infos returned)'); return }

  if (!fetchPools) {
    console.error('❌ SDK missing a "fetch pools" function.')
    console.error('   clmmInstanceKeys:', clmmKeys)
    process.exit(2)
  }
  const poolIds = Array.from(new Set(
    posInfos.map((p:any)=> (p.poolId?.toBase58?.() ?? String(p.poolId))).filter(Boolean)
  )).map((s)=> new PublicKey(s))
  const pools = await fetchPools({ connection, poolIds })

  if (!fetchMultipleMintInfos) {
    console.error('❌ SDK missing fetchMultipleMintInfos; cannot compute UI amounts.')
    process.exit(2)
  }
  const mintSet = new Set<string>()
  for (const p of pools) {
    const a = p.mintA?.mint?.toBase58?.() ?? String(p.mintA?.mint ?? '')
    const b = p.mintB?.mint?.toBase58?.() ?? String(p.mintB?.mint ?? '')
    if (a) mintSet.add(a); if (b) mintSet.add(b)
  }
  const mintInfos = await fetchMultipleMintInfos({ connection, mints: Array.from(mintSet).map(m=>new PublicKey(m)) })

  let priceMap: Record<string, number> = {}
  if (priceMultiple) {
    priceMap = (await priceMultiple({ tokenMints: Array.from(mintSet), connection, raydium: ray })) || {}
  }

  if (!amountsFromLiquidity) {
    console.error('❌ SDK missing a liquidity→amounts function.')
    console.error('   clmmInstanceKeys:', clmmKeys)
    process.exit(2)
  }

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

    const res = await amountsFromLiquidity({
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
      `$${usd.toSignificantDigits(6).toString()}`
    )
  }

  console.log('\nTotal ≈', `$${total.toSignificantDigits(8).toString()}`)
}

main().catch((e)=>{ console.error('Fatal:', e); process.exit(1) })
