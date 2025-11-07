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

const WSOL_MINT = 'So11111111111111111111111111111111111111112'
const USDC_MINT = 'EPjFWdd5AufqSSqeM2qW7AqW9bWpMCHqvfz4xY3Us6w'

const short = (s: string) => (s.length > 12 ? `${s.slice(0, 6)}…${s.slice(-6)}` : s)

function isValidPkStr(s: string) {
  try {
    new PublicKey(s)
    return true
  } catch {
    return false
  }
}

async function discoverOwnerMints(conn: Connection, owner: PublicKey) {
  const TOKEN_2018 = new PublicKey('EbKbEKnKZvdW4Z8pnG1CigrL29wLw6UYJvB1s9ujxa3e')
  const resp: any = await (conn as any).getParsedTokenAccountsByOwner(owner, { programId: TOKEN_2018 })
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

function computeUsdForSolUsdc(
  mintA: string,
  mintB: string,
  amountA: Decimal,
  amountB: Decimal,
  priceBPerA: Decimal,
) {
  if (mintA === WSOL_MINT && mintB === USDC_MINT) {
    return amountA.mul(priceBPerA).add(amountB)
  }
  if (mintA === USDC_MINT && mintB === WSOL_MINT) {
    if (priceBPerA.isZero()) return null
    const priceUsdcPerSol = new Decimal(1).div(priceBPerA)
    return amountB.mul(priceUsdcPerSol).add(amountA)
  }
  return null
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

  const targets: {
    mint: PublicKey
    posPk: PublicKey
    poolId: PublicKey
    position: ReturnType<typeof PositionInfoLayout.decode>
  }[] = []

  for (const m of mints) {
    let mintPk: PublicKey
    try {
      mintPk = new PublicKey(m)
    } catch (e) {
      console.error('Invalid mint', m, '-', (e as any)?.message || e)
      continue
    }

    const { publicKey: posPk } = getPdaPersonalPositionAddress(CLMM_ID, mintPk)
    const posAcc = await conn.getAccountInfo(posPk)
    if (!posAcc?.data) {
      console.error('No position account found for mint', m)
      continue
    }
    let pos
    try {
      pos = PositionInfoLayout.decode(posAcc.data)
    } catch (e) {
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

  const uniquePoolKeys = [...new Map(targets.map(t => [t.poolId.toBase58(), t.poolId])).values()]
  const poolAccounts = await conn.getMultipleAccountsInfo(uniquePoolKeys)
  const poolMap = new Map<string, ReturnType<typeof PoolInfoLayout.decode>>()
  uniquePoolKeys.forEach((pk, idx) => {
    const acc = poolAccounts[idx]
    if (acc?.data) {
      try {
        poolMap.set(pk.toBase58(), PoolInfoLayout.decode(acc.data))
      } catch (e) {
        console.error('Failed to decode pool', pk.toBase58(), '-', (e as any)?.message || e)
      }
    }
  })

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
      rows.push({
        poolPk: poolIdStr,
        posMint: target.mint.toBase58(),
        tokenA: '-',
        tokenB: '-',
        usd: '-',
      })
      continue
    }

    const priceDecimal = priceFromSqrt(pool)
    const poolInfoForMath = {
      price: priceDecimal.toString(),
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

      const mintA = pool.mintA.toBase58()
      const mintB = pool.mintB.toBase58()
      usdValue = computeUsdForSolUsdc(mintA, mintB, amountAUi, amountBUi, priceDecimal)
    } catch (e) {
      console.error(
        'Failed to compute liquidity amounts for position',
        target.mint.toBase58(),
        '-',
        (e as any)?.message || e,
      )
    }

    const mintA = pool.mintA.toBase58()
    const mintB = pool.mintB.toBase58()

    rows.push({
      poolPk: poolIdStr,
      posMint: target.mint.toBase58(),
      tokenA: amountAUi
        ? `${amountAUi.toSignificantDigits(6).toString()} ${short(mintA)}`
        : `- ${short(mintA)}`,
      tokenB: amountBUi
        ? `${amountBUi.toSignificantDigits(6).toString()} ${short(mintB)}`
        : `- ${short(mintB)}`,
      usd: usdValue ? `$${usdValue.toSignificantDigits(6).toString()}` : '-',
    })
  }

  console.log('\n💎 Raydium CL Positions (via PDA decode)\n')
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
