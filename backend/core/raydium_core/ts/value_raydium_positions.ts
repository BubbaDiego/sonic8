// @ts-nocheck
import 'dotenv/config'
import { Connection, PublicKey } from '@solana/web3.js'
import Decimal from 'decimal.js'

// Prefer v2, fallback v1
let SDK: any = {}
try { SDK = require('@raydium-io/raydium-sdk-v2') } catch {}
if (!SDK || !Object.keys(SDK).length) {
  try { SDK = require('@raydium-io/raydium-sdk') } catch {}
}
if (!SDK || !Object.keys(SDK).length) {
  console.error('❌ Could not load @raydium-io/raydium-sdk[-v2]. Install one of them in ./ts folder.')
  process.exit(2)
}

const RPC = process.env.RPC_URL || process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com'
const args = process.argv.slice(2)
function arg(flag: string) { const i = args.indexOf(flag); return i >= 0 ? args[i+1] : undefined }

const ownerStr = arg('--owner')
const mintsCsv = arg('--mints')
const owner = ownerStr ? new PublicKey(ownerStr) : undefined
const inputMints = (mintsCsv ? mintsCsv.split(',').map(s=>s.trim()).filter(Boolean) : []) as string[]

const short = (s: string) => `${s.slice(0, 6)}…${s.slice(-6)}`

// pull candidates by dotted path (deep)
function getDeep(obj: any, paths: string[]): any {
  for (const p of paths) {
    const parts = p.split('.')
    let cur = obj
    let ok = true
    for (const part of parts) {
      if (cur && (part in cur)) cur = cur[part]; else { ok = false; break }
    }
    if (ok && typeof cur === 'function') return cur.bind(obj)
    if (ok && typeof cur === 'object') return cur
  }
  return undefined
}

async function main() {
  const connection = new Connection(RPC, 'confirmed')

  // Find top-level Raydium
  const Raydium = SDK.Raydium || SDK.raydium || getDeep(SDK, ['default.Raydium'])
  if (!Raydium) {
    console.error('❌ Raydium client class not found. SDK keys:', Object.keys(SDK))
    process.exit(2)
  }
  const ray = await Raydium.load?.({ connection })
  if (!ray) {
    console.error('❌ Raydium.load failed. SDK keys:', Object.keys(SDK))
    process.exit(2)
  }

  // Find CLMM namespace/object
  const Clmm =
    SDK.Clmm || SDK.CLMM || SDK.clmm ||
    getDeep(SDK, ['default.Clmm','default.CLMM']) ||
    getDeep(SDK, ['ClmmPool','default.ClmmPool']) ||
    getDeep(SDK, ['CLMM','default.CLMM']) ||
    {}

  // Show EVERYTHING we can see so we know what this package looks like
  const clmmKeys = Clmm && typeof Clmm === 'object' ? Object.keys(Clmm) : []
  console.log('🔧 SDK check →', JSON.stringify({
    rootKeys: Object.keys(SDK),
    clmmType: typeof Clmm,
    clmmKeysCount: clmmKeys.length,
    clmmKeys: clmmKeys,
  }, null, 2), '\n')

  // Helper to find a function by many names and also inside sub-namespaces
  function pickFn(candidates: string[], alsoCheck: string[] = []) {
    for (const name of candidates) {
      if (Clmm && typeof Clmm[name] === 'function') return Clmm[name].bind(Clmm)
    }
    for (const ns of alsoCheck) {
      const sub = getDeep(Clmm, [ns])
      if (!sub) continue
      for (const name of candidates) {
        if (sub && typeof sub[name] === 'function') return sub[name].bind(sub)
      }
    }
    return undefined
  }

  const fetchPositionsByOwner = pickFn(
    ['fetchPositionsByOwner','fetchPositionsByUser','getPositionsByOwner','getPositionsByUser'],
    ['Position','Positions','User','Users']
  )
  const fetchPositionInfos = pickFn(
    ['fetchPositionInfos','fetchPositionsInfo','getPositionInfos','getPositionsInfo','getPositionsByMints','fetchPositionsByMints'],
    ['Position','Positions']
  )
  const fetchPools = pickFn(
    ['fetchMultiplePoolInfos','fetchPools','getMultiplePoolInfos','getPools'],
    ['Pool','Pools']
  )
  const amountsFromLiq = pickFn(
    ['getAmountsFromLiquidity','liquidityToTokenAmounts','getTokenAmountsFromLiquidity'],
    ['Math','Maths','Utils','ClmmMath','ClmmUtils']
  )
  const fetchMintInfos = SDK.fetchMultipleMintInfos
    || SDK.MintUtil?.fetchMultipleMintInfos
    || SDK.Token?.fetchMultipleMintInfos
    || getDeep(SDK, ['Utils.fetchMultipleMintInfos','Token.fetchMultipleMintInfos','default.fetchMultipleMintInfos'])

  const Price = SDK.Price || SDK.price || {}
  const priceMultiple = (Price && (Price.fetchMultiple || Price.getMultiple || Price.getPrices))
    ? (Price.fetchMultiple || Price.getMultiple || Price.getPrices).bind(Price)
    : undefined

  // Build position mint list
  let positionMints: PublicKey[] = []
  if (inputMints.length) {
    try { positionMints = inputMints.map((m)=>new PublicKey(m)) } catch (e) {
      console.error('❌ Invalid mint in --mints:', e); process.exit(2)
    }
  } else if (owner && fetchPositionsByOwner) {
    const briefs = await fetchPositionsByOwner({ connection, owner })
    if (!briefs?.length) { console.log('   (no positions for owner)'); return }
    positionMints = briefs.map((b:any)=> new PublicKey(b.positionNftMint ?? b.mint ?? b.nftMint))
  } else {
    console.error('❌ No --mints and no positions-by-owner method found.')
    console.error('   clmmKeys:', clmmKeys)
    process.exit(2)
  }

  if (!fetchPositionInfos) {
    console.error('❌ SDK missing a "fetch position infos" function.')
    console.error('   clmmKeys:', clmmKeys)
    process.exit(2)
  }
  const posInfos = await fetchPositionInfos({ connection, positions: positionMints })
  if (!posInfos?.length) { console.log('   (no position infos returned)'); return }

  if (!fetchPools) {
    console.error('❌ SDK missing a "fetch pools" function.')
    console.error('   clmmKeys:', clmmKeys)
    process.exit(2)
  }
  const poolIds = Array.from(new Set(
    posInfos.map((p:any)=> (p.poolId?.toBase58?.() ?? String(p.poolId))).filter(Boolean)
  )).map((s)=> new PublicKey(s))
  const pools = await fetchPools({ connection, poolIds })

  if (!fetchMintInfos) {
    console.error('❌ SDK missing fetchMultipleMintInfos; cannot compute UI amounts.')
    process.exit(2)
  }

  // Collect mints for decimals & prices
  const mintSet = new Set<string>()
  for (const p of pools) {
    const a = p.mintA?.mint?.toBase58?.() ?? String(p.mintA?.mint ?? '')
    const b = p.mintB?.mint?.toBase58?.() ?? String(p.mintB?.mint ?? '')
    if (a) mintSet.add(a); if (b) mintSet.add(b)
  }
  const mintInfos = await fetchMintInfos({ connection, mints: Array.from(mintSet).map(m=>new PublicKey(m)) })
  let priceMap: Record<string, number> = {}
  if (priceMultiple) {
    priceMap = (await priceMultiple({ tokenMints: Array.from(mintSet), connection, raydium: ray })) || {}
  }

  if (!amountsFromLiq) {
    console.error('❌ SDK missing a liquidity→amounts function.')
    console.error('   clmmKeys:', clmmKeys)
    process.exit(2)
  }

  // Index pools by id
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

    const res = await amountsFromLiq({
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
