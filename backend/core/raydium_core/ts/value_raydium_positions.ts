// @ts-nocheck
import 'dotenv/config'
import { Connection, PublicKey } from '@solana/web3.js'
import Decimal from 'decimal.js'

// Load Raydium SDK (v2 preferred, fallback v1)
let SDK: any = {}
try { SDK = require('@raydium-io/raydium-sdk-v2') } catch {}
if (!SDK || !Object.keys(SDK).length) { try { SDK = require('@raydium-io/raydium-sdk') } catch {} }
if (!SDK || !Object.keys(SDK).length) {
  console.error('❌ Could not load @raydium-io/raydium-sdk[-v2]. Install one of them in ./ts.')
  process.exit(2)
}

// Helpers to normalize differences across versions
const getDeep = (obj: any, path: string) =>
  path.split('.').reduce((a, k) => (a && k in a ? a[k] : undefined), obj)

const PositionInfoLayout =
  SDK.PositionInfoLayout || SDK.ProtocolPositionLayout || SDK.PositionInfo || SDK.PositionLayout
const PoolInfoLayout     =
  SDK.PoolInfoLayout     || SDK.ClmmPoolInfoLayout    || SDK.PoolLayout      || SDK.PoolInfo

const _clmmPid =
  SDK.CLMM_PROGRAM_ID?.toBase58?.() ||
  SDK.CLMM_PROGRAM_ID ||
  getDeep(SDK, 'default.CLMM_PROGRAM_ID')?.toBase58?.() ||
  getDeep(SDK, 'default.CLMM_PROGRAM_ID') ||
  ''
const CLMM_PROGRAM_ID = _clmmPid ? new PublicKey(String(_clmmPid)) : new PublicKey('CLMMm7ctS5Xw2qVTL4x1X2LFkW1zD6kH19V7S8hKQ2k') // fallback

const fetchMultipleMintInfos =
  SDK.fetchMultipleMintInfos ||
  SDK.MintUtil?.fetchMultipleMintInfos ||
  SDK.Token?.fetchMultipleMintInfos

const Price = SDK.Price || SDK.price || {}
const priceMultiple = (Price.fetchMultiple || Price.getMultiple || Price.getPrices)?.bind(Price)

if (!PositionInfoLayout || !PoolInfoLayout) {
  console.error('❌ SDK missing PositionInfoLayout / PoolInfoLayout. Keys:', Object.keys(SDK))
  process.exit(2)
}

// Args
const RPC = process.env.RPC_URL || process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com'
const args = process.argv.slice(2)
const arg = (f: string) => { const i = args.indexOf(f); return i >= 0 ? args[i+1] : undefined }
const ownerStr = arg('--owner')
const mintsCsv = arg('--mints')
const owner = ownerStr ? new PublicKey(ownerStr) : undefined
const inputMints = (mintsCsv ? mintsCsv.split(',').map(s=>s.trim()).filter(Boolean) : []) as string[]

// Utils
const short = (s: string) => `${s.slice(0, 6)}…${s.slice(-6)}`
const TWO_64 = new Decimal(2).pow(64)
const ONE_0001 = new Decimal('1.0001')
const q64ToDecimal = (q: bigint | number | string) => new Decimal(q.toString()).div(TWO_64)
const sqrtPriceFromTick = (tick: number) => ONE_0001.pow(tick).sqrt()
function tryPk(s: string | undefined): PublicKey | null { try { return s ? new PublicKey(s) : null } catch { return null } }

function amountsFromLiquidity(L: Decimal, sqrtLower: Decimal, sqrtCur: Decimal, sqrtUpper: Decimal) {
  if (sqrtCur.lte(sqrtLower)) {
    const amt0 = L.mul(sqrtUpper.minus(sqrtLower)).div(sqrtLower.mul(sqrtUpper))
    return { amt0, amt1: new Decimal(0) }
  } else if (sqrtCur.gte(sqrtUpper)) {
    const amt1 = L.mul(sqrtUpper.minus(sqrtLower))
    return { amt0: new Decimal(0), amt1 }
  } else {
    const amt0 = L.mul(sqrtUpper.minus(sqrtCur)).div(sqrtCur.mul(sqrtUpper))
    const amt1 = L.mul(sqrtCur.minus(sqrtLower))
    return { amt0, amt1 }
  }
}

// PDA from mint (SDK helper if present, else seeds ["position", mint])
function getPositionPdaFromMint(mint: PublicKey): PublicKey {
  const helper =
    SDK.getPdaPersonalPositionAddress ||
    SDK.getPdaPersonalPosition ||
    SDK.PositionUtils?.getPdaPersonalPositionAddress
  if (helper) {
    const out = helper({ mint }) || helper(mint)
    const key = out?.publicKey || out?.address || out
    return key instanceof PublicKey ? key : new PublicKey(String(key))
  }
  const [addr] = PublicKey.findProgramAddressSync([Buffer.from('position'), mint.toBuffer()], CLMM_PROGRAM_ID)
  return addr
}

// Fallback owner scan: NFT-like (decimals==0 and amount>=1), robust to token-2022 id parsing
async function discoverCandidateMintsByOwner(connection: Connection, owner: PublicKey): Promise<string[]> {
  const programs: (PublicKey | null)[] = [
    tryPk('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'), // Token (legacy)
    tryPk('TokenzQdBNbLqP5dK3W3dH7hJZ8Fj5nV9vWwHES1s6Cw'), // Token-2022 (skip if invalid here)
  ].filter(Boolean) as PublicKey[]

  const mints: string[] = []
  for (const program of programs) {
    try {
      const resp = await (connection as any).getParsedTokenAccountsByOwner(owner, { programId: program })
      const items = resp?.value || resp?.result?.value || []
      for (const it of items) {
        try {
          const info = it.account?.data?.parsed?.info || it?.data?.parsed?.info
          const tA   = info?.tokenAmount
          const amount = Number(tA?.amount ?? 0)
          const decimals = Number(tA?.decimals ?? 0)
          if (decimals === 0 && amount >= 1) {
            const mint = String(info?.mint || '')
            if (mint && !mints.includes(mint)) mints.push(mint)
          }
        } catch {}
      }
    } catch {}
  }
  return mints
}

async function main() {
  const connection = new Connection(RPC, 'confirmed')

  let mintStrings = inputMints.slice()
  if (!mintStrings.length && owner) {
    console.log('🔎 No --mints provided; scanning owner token accounts for NFT-like candidates…')
    mintStrings = await discoverCandidateMintsByOwner(connection, owner)
  }
  if (!mintStrings.length) {
    console.error('❌ No candidate mints. Pass --mints <M1[,M2,…]> or ensure owner has an NFT-like CLMM position token.')
    process.exit(2)
  }

  const mintPks = mintStrings.map((m) => new PublicKey(m))
  const posPdas = mintPks.map(getPositionPdaFromMint)

  // fetch & decode positions
  const posInfos = await connection.getMultipleAccountsInfo(posPdas, { commitment: 'confirmed' })
  type PositionDecoded = { poolId: PublicKey; tickLower: number; tickUpper: number; liquidity: Decimal; positionMint: PublicKey }
  const decodedPositions: PositionDecoded[] = []

  for (let i = 0; i < posInfos.length; i++) {
    const ai = posInfos[i]
    if (!ai?.data) continue
    const buf = Buffer.from(ai.data as Buffer)
    const dec: any = PositionInfoLayout.decode(buf)

    const poolId = new PublicKey(dec.poolId ?? dec.pool_id ?? dec.poolKey ?? dec.pool ?? dec.poolAddress)
    const tickLower = Number(dec.tickLowerIndex ?? dec.tickLower ?? dec.lowerTick ?? dec.tickLowerIdx)
    const tickUpper = Number(dec.tickUpperIndex ?? dec.tickUpper ?? dec.upperTick ?? dec.tickUpperIdx)

    let liquidityRaw: any =
      dec.liquidity !== undefined ? dec.liquidity :
      dec.liq !== undefined ? dec.liq :
      dec.liquidityAmount !== undefined ? dec.liquidityAmount :
      (dec.L !== undefined ? dec.L : 0)

    const liqStr =
      typeof liquidityRaw === 'bigint' ? liquidityRaw.toString() :
      typeof liquidityRaw === 'number' ? String(liquidityRaw) :
      (typeof liquidityRaw === 'string' ? liquidityRaw : '0')

    decodedPositions.push({
      poolId,
      tickLower,
      tickUpper,
      liquidity: new Decimal(liqStr),
      positionMint: mintPks[i],
    })
  }

  if (!decodedPositions.length) {
    console.log('   (no decodable CLMM positions among candidates)')
    return
  }

  // fetch & decode pools
  const uniquePoolIds = Array.from(new Set(decodedPositions.map(p => p.poolId.toBase58()))).map(s => new PublicKey(s))
  const poolInfos = await connection.getMultipleAccountsInfo(uniquePoolIds, { commitment: 'confirmed' })

  const poolById: Record<string, { sqrtPriceQ64: bigint; mintA: PublicKey; mintB: PublicKey }> = {}
  for (let i = 0; i < uniquePoolIds.length; i++) {
    const pk = uniquePoolIds[i]
    const ai = poolInfos[i]
    if (!ai?.data) continue
    const buf = Buffer.from(ai.data as Buffer)
    const dec: any = PoolInfoLayout.decode(buf)

    const sqrtPriceX64 = dec.sqrtPriceX64 ?? dec.sqrtPrice ?? dec.sqrt_price_x64 ?? dec.currentPrice
    const mintA = new PublicKey(dec.mintA?.mint ?? dec.mintA ?? dec.tokenMintA ?? dec.mint_a)
    const mintB = new PublicKey(dec.mintB?.mint ?? dec.mintB ?? dec.tokenMintB ?? dec.mint_b)
    const sqrtStr = typeof sqrtPriceX64 === 'bigint' ? sqrtPriceX64.toString() : String(sqrtPriceX64)

    poolById[pk.toBase58()] = { sqrtPriceQ64: BigInt(sqrtStr), mintA, mintB }
  }

  // decimals
  if (!fetchMultipleMintInfos) {
    console.error('❌ SDK missing fetchMultipleMintInfos; cannot compute UI amounts safely.')
    process.exit(2)
  }
  const mintSet = new Set<string>()
  Object.values(poolById).forEach(p => { mintSet.add(p.mintA.toBase58()); mintSet.add(p.mintB.toBase58()) })
  const mintInfos = await fetchMultipleMintInfos({ connection, mints: Array.from(mintSet).map(s => new PublicKey(s)) })

  // prices (best-effort)
  let priceMap: Record<string, number> = {}
  if (priceMultiple) {
    priceMap = (await priceMultiple({ tokenMints: Array.from(mintSet), connection })) || {}
  }

  // compute amounts & USD
  let totalUsd = new Decimal(0)
  console.log('\n💎 Raydium CL Positions (raw chain decode)\n')
  console.log('Pool'.padEnd(12), 'Position'.padEnd(14), 'TokenA'.padEnd(22), 'TokenB'.padEnd(22), 'USD')

  for (const pos of decodedPositions) {
    const pool = poolById[pos.poolId.toBase58()]
    if (!pool) continue

    const sqrtCur = q64ToDecimal(pool.sqrtPriceQ64)
    const sqrtLower = sqrtPriceFromTick(pos.tickLower)
    const sqrtUpper = sqrtPriceFromTick(pos.tickUpper)
    const { amt0, amt1 } = amountsFromLiquidity(pos.liquidity, sqrtLower, sqrtCur, sqrtUpper)

    const mintA = pool.mintA.toBase58()
    const mintB = pool.mintB.toBase58()
    const decA = mintInfos[mintA]?.decimals ?? 0
    const decB = mintInfos[mintB]?.decimals ?? 0

    const uiA = amt0
    const uiB = amt1

    const pA = new Decimal(priceMap[mintA] ?? 0)
    const pB = new Decimal(priceMap[mintB] ?? 0)
    const usd = uiA.mul(pA).add(uiB.mul(pB))
    totalUsd = totalUsd.add(usd)

    const symA = SDK.Token?.SOLMint?.equals?.(pool.mintA) ? 'SOL' : (SDK.toToken?.(mintA)?.symbol ?? short(mintA))
    const symB = SDK.Token?.SOLMint?.equals?.(pool.mintB) ? 'SOL' : (SDK.toToken?.(mintB)?.symbol ?? short(mintB))

    console.log(
      short(pos.poolId.toBase58()).padEnd(12),
      short(pos.positionMint.toBase58()).padEnd(14),
      `${uiA.toSignificantDigits(6).toString()} ${symA}`.padEnd(22),
      `${uiB.toSignificantDigits(6).toString()} ${symB}`.padEnd(22),
      `$${usd.toSignificantDigits(6).toString()}`
    )
  }

  console.log('\nTotal ≈', `$${totalUsd.toSignificantDigits(8).toString()}`)
}

main().catch(e => { console.error('Fatal:', e); process.exit(1) })
