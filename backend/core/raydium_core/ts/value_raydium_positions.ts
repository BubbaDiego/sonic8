/**
 * Value Raydium CLMM positions for an owner:
 * - Finds CL position NFTs owned by --owner
 * - Resolves their associated CLMM position PDAs
 * - Computes tokenA/tokenB amounts from liquidity & current price
 * - Fetches token prices; prints per-position + total USD
 *
 * Requires network access (SDK endpoints).
 */
import 'dotenv/config'
import { Connection, PublicKey } from '@solana/web3.js'
import { Raydium, Clmm, Price, Token, TokenAmount, ApiClmmPoolsItem, fetchMultipleMintInfos } from '@raydium-io/raydium-sdk-v2'
import Decimal from 'decimal.js'

const RPC = process.env.RPC_URL || process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com'
const ownerArg = process.argv[process.argv.indexOf('--owner') + 1]
if (!ownerArg) {
  console.error('Usage: ts-node value_raydium_positions.ts --owner <PUBKEY>')
  process.exit(2)
}

const owner = new PublicKey(ownerArg)

function short(s: string) {
  return `${s.slice(0, 6)}…${s.slice(-6)}`
}

async function main() {
  const connection = new Connection(RPC, 'confirmed')
  const ray = await Raydium.load({ connection })

  // 1) Discover CLMM positions by owner via SDK helper
  //    This returns position PDAs and pool keys
  const posBriefs = await Clmm.fetchPositionsByOwner({ connection, owner })

  if (posBriefs.length === 0) {
    console.log('   (no Raydium CLMM positions found)')
    return
  }

  // 2) Fetch full position + pool info
  const poolsNeeded = Array.from(new Set(posBriefs.map(p => p.poolId.toBase58())))
  const pools = await Clmm.fetchMultiplePoolInfos({ connection, poolIds: poolsNeeded.map(p => new PublicKey(p)) })
  const posInfos = await Clmm.fetchPositionInfos({ connection, positions: posBriefs.map(p => p.positionNftMint) })

  // 3) Build token registry for pricing (from pools’ mints)
  const mintSet = new Set<string>()
  pools.forEach(p => { mintSet.add(p.mintA.mint.toBase58()); mintSet.add(p.mintB.mint.toBase58()) })
  const mintInfos = await fetchMultipleMintInfos({ connection, mints: Array.from(mintSet).map(m => new PublicKey(m)) })

  // 4) Fetch prices (SDK price map; fallback to Raydium/Jup inside SDK)
  const priceMap = await Price.fetchMultiple({ tokenMints: Array.from(mintSet), connection, raydium: ray })

  // 5) Walk positions → compute token amounts and USD
  let totalUsd = new Decimal(0)

  console.log('\n💎 Raydium CL Positions (owner:', owner.toBase58(), ')\n')
  console.log('Pool'.padEnd(12), 'Position'.padEnd(14), 'TokenA'.padEnd(20), 'TokenB'.padEnd(20), 'USD')

  for (const br of posBriefs) {
    const pos = posInfos.find(p => p.positionNftMint.equals(br.positionNftMint))
    const pool = pools.find(p => p.id.equals(br.poolId))
    if (!pos || !pool) continue

    // Compute token amounts at current price
    const { amountA, amountB } = Clmm.getAmountsFromLiquidity({
      poolInfo: pool,
      tickLower: pos.tickLower,
      tickUpper: pos.tickUpper,
      liquidity: pos.liquidity
    })

    const mintA = pool.mintA.mint.toBase58()
    const mintB = pool.mintB.mint.toBase58()
    const decA = mintInfos[mintA].decimals
    const decB = mintInfos[mintB].decimals

    const uiA = new Decimal(amountA.toString()).div(new Decimal(10).pow(decA))
    const uiB = new Decimal(amountB.toString()).div(new Decimal(10).pow(decB))

    const pA = new Decimal(priceMap[mintA] ?? 0)
    const pB = new Decimal(priceMap[mintB] ?? 0)
    const usd = uiA.mul(pA).add(uiB.mul(pB))
    totalUsd = totalUsd.add(usd)

    const symA = pool.mintA.symbol ?? short(mintA)
    const symB = pool.mintB.symbol ?? short(mintB)
    console.log(
      short(pool.id.toBase58()).padEnd(12),
      short(pos.positionNftMint.toBase58()).padEnd(14),
      `${uiA.toSignificantDigits(6).toString()} ${symA}`.padEnd(20),
      `${uiB.toSignificantDigits(6).toString()} ${symB}`.padEnd(20),
      `$${usd.toSignificantDigits(6).toString()}`
    )
  }

  console.log('\nTotal ≈', `$${totalUsd.toSignificantDigits(8).toString()}`)
}

main().catch(err => {
  console.error('Fatal:', err)
  process.exit(1)
})
