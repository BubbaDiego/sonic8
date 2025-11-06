// @ts-check
import 'dotenv/config'
import { Connection, PublicKey } from '@solana/web3.js'
import bs58 from 'bs58'
import Decimal from 'decimal.js'

// Optional: we only use SDK for CLMM program id and (if available) a price helper
let SDK: any = {}
try { SDK = require('@raydium-io/raydium-sdk-v2') } catch {}
if (!Object.keys(SDK).length) { try { SDK = require('@raydium-io/raydium-sdk') } catch {} }

const CLMM_ID: PublicKey = (() => {
  try { return new PublicKey(SDK?.CLMM_PROGRAM_ID) } catch { return new PublicKey('CAMMCzo5YL8w4VFF8KVHrK22GGu77ZhgGB9jXa8i74G') /* fallback, replace if needed */ }
})()

// optional price helper if present
const Price = (SDK as any)?.price || (SDK as any)?.Price || null
const fetchPrices: null | ((args: any) => Promise<Record<string, string|number>>) =
  (Price && (Price.fetchMultiple || (Price.getMultiple || (Price.getPrices || null)))) || null

const RPC = process.env.RPC_URL || process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com'

const argv = process.argv.slice(2)
const arg = (k: string) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : undefined }
const ownerStr = arg('--owner') // present but not required when --mints is given
const mintsCsv = arg('--mints')
const mintList: string[] = (mintsCsv ? mintsCsv.split(',').map(s => s.trim()).filter(Boolean) : [])

const U64 = new Decimal(1).times(2).pow(64)
const sqrtFromTick = (t: number) => new Decimal(1.0001).pow(t)
const q128ToDec = (lo: bigint, hi: bigint) => new Decimal(hi.toString()).times(2 ** 64).add(new Decimal(lo.toString()))
const short = (s: string) => (s.length > 12 ? `${s.slice(0,6)}…${s.slice(-6)}` : s)

function isValidPkStr(s: string) { try { new (require('@solana/web3.js').PublicKey)(s); return true } catch { return false } }

async function findPositionAccountsByMint(conn: Connection, programId: PublicKey, mint: PublicKey) {
  // We *must* filter; scanning the whole program hits RPC 10MB limit.
  // Raydium CLMM "personal position" account contains the position NFT mint as a 32-byte field.
  // Its exact offset changed between versions; we probe a few likely offsets.
  const mintBs58 = bs58.encode(mint.toBuffer())
  const candidateOffsets = [8, 40, 72, 104, 136, 168] // probe several plausible 32-byte field offsets
  const sizeHints = [216, 248, 272] // v1/v2 position account sizes observed

  for (const size of sizeHints) {
    for (const off of candidateOffsets) {
      try {
        const res: any = await (conn as any).getProgramAccounts(programId, {
          commitment: 'confirmed',
          filters: [{ dataSize: size }, { memcmp: { offset: off, bytes: mintBs58 } }],
          encoding: 'base64',
        })
        if (res?.value?.length) return res.value
      } catch { /* keep probing */ }
    }
  }
  return []
}

function decodePositionLoose(data: Buffer) {
  // Try to locate pool/mint/ticks/liquidity without relying on SDK layout.
  // Strategy:
  // 1) Find all 32-byte windows that are valid Pubkeys -> collect candidates.
  // 2) One of them equals the position NFT mint (we’ll provide that externally).
  // 3) The pool pubkey is another 32B field in this account whose owner == CLMM program.
  // 4) Ticks are two adjacent little-endian i32 near the mint or pool fields.
  // 5) Liquidity is a u128 near the ticks.

  return {
    tryParse(mintPk: PublicKey) {
      const mintBytes = mintPk.toBytes()
      const idx = data.indexOf(Buffer.from(mintBytes))
      if (idx < 0) return null

      // Look around the mint field ±64 bytes to find two consecutive i32 ticks and a nearby u128 (liquidity).
      const windowStart = Math.max(0, idx - 96)
      const windowEnd = Math.min(data.length, idx + 128)
      const view = new DataView(data.buffer, data.byteOffset + windowStart, windowEnd - windowStart)

      let best: any = null
      for (let off = 0; off + 8 < view.byteLength; off++) {
        // read two little-endian i32 (tickLower, tickUpper)
        const tL = view.getInt32(off, true)
        const tU = view.getInt32(off + 4, true)
        // Raydium CLMM ticks are multiples of 1/√(1.0001) exponents, so |tick| typically < 1e6
        if (Math.abs(tL) > 1_000_000 || Math.abs(tU) > 1_000_000) continue
        // try liquidity just after ticks (16 bytes)
        const lo = view.getBigUint64(off + 8, true)
        const hi = view.getBigUint64(off + 16, true)
        const L = q128ToDec(lo, hi)
        if (L.isFinite() && L.gt(0)) {
          best = { tickL: tL, tickU: tU, L }
          break
        }
      }
      if (!best) return null

      // Probe for a nearby 32B that looks like a pool account (owner == CLMM program).
      const neighbors: Buffer[] = []
      const around = [idx - 64, idx - 32, idx + 32, idx + 64]
      for (const start of around) {
        if (start >= 0 && start + 32 <= data.length) {
          neighbors.push(data.subarray(start, start + 32))
        }
      }

      return { mint: mintPk, neighbors, ...best }
    }
  }
}

(async () => {
  const conn = new Connection(RPC, 'confirmed')

  let mints = [...new Set(mintList)]
  if (mints.length === 0) {
    if (!ownerStr) {
      console.error('No --mints provided and no --owner to scan; supply --mints <M1[,M2…]>.')
      process.exit(2)
    }
    // scan owner’s SPL-Token accounts for 1-unit NFTs
    const owner = new PublicKey(ownerStr)
    const TOKEN_2018 = new PublicKey('EbKbEKnKZvdW4Z8pnG1CigrL29wLw6UYJvB1s9ujxa3e') // SPL Token 2022 can be non-base58 on some builds; use legacy program to avoid throw
    try {
      const resp: any = await (conn as any).getParsedTokenAccountsByOwner(owner, { programId: TOKEN_2018 })
      const items = resp?.value || []
      for (const it of items) {
        const info = it.account?.data?.parsed?.info
        const dec = Number(info?.tokenAmount?.decimals || 0)
        const amt = new Decimal(String(info?.tokenAmount?.amount || '0'))
        const mint = String(info?.mint || '')
        if (dec === 0 && mint && isValidPkStr(mint) && amt.gt(0)) mints.push(mint)
      }
      mints = [...new Set(mints)]
      if (!mints.length) {
        console.error('No NFT-like tokens found for owner; pass --mints <M1[,M2…]>.')
        process.exit(2)
      }
    } catch (e) {
      console.error('Owner scan failed, pass --mints explicitly. Detail:', (e as any)?.message || e)
      process.exit(1)
    }
  }

  // For each mint, find the position account via filtered program accounts (probe likely offsets + size)
  const targets: { mint: PublicKey; posPk: PublicKey }[] = []
  for (const m of mints) {
    const mintPk = new PublicKey(m)
    const accounts = await findPositionAccountsByMint(conn, CLMM_ID, mintPk)
    if (!accounts.length) {
      console.error('No position account found for mint', m)
      continue
    }
    // usually it’s a single hit; if multiple, take the one with smallest data size
    accounts.sort((a:any, b:any) => (a.account.data[0].length ?? 0) - (b.account.data[0].length ?? 0))
    targets.push({ mint: mintPk, posPk: accounts[0].pubkey })
  }
  if (!targets.length) {
    console.error('No matching CLMM position accounts; cannot value.')
    process.exit(2)
  }

  // Read and decode each position + its pool
  const posInfos = await Promise.all(targets.map(t => (conn as any).getAccountInfo(t.posPk, { commitment: 'confirmed' })))
  const rows: any[] = []
  for (let i = 0; i < targets.length; i++) {
    const t = targets[i]
    const acc: any = posInfos[i]
    if (!acc?.data) continue
    const parsed = decodePositionLoose(Buffer.from(acc.data)).tryParse(t.mint)
    if (!parsed) {
      console.error('Could not parse ticks/liquidity for mint', t.mint.toBase58(), '— will print raw account and skip value.')
      rows.push({ poolPk: '(unknown)', posMint: t.mint.toBase58(), tokenA: '-', tokenB: '-', usd: '-' })
      continue
    }
    // Choose neighbor that is a CLMM-owned account as pool
    let poolPk: PublicKey | null = null
    for (const nb of parsed.neighbors) {
      try {
        const pk = new PublicKey(nb)
        const info = await (conn as any).getAccountInfo(pk, { commitment: 'confirmed' })
        if (info?.owner?.equals(CLMM_ID)) { poolPk = pk; break }
      } catch { /* skip */ }
    }
    if (!poolPk) {
      rows.push({ poolPk: '(no-match)', posMint: parsed.mint.toBase58(), tokenA: '-', tokenB: '-', usd: '-' })
      continue
    }

    // read pool to get sqrtPrice and mints (mint decimals)
    const poolAcc: any = await (conn as any).getAccountInfo(poolPk, { commitment: 'confirmed' })
    if (!poolAcc?.data) {
      rows.push({ poolPk: poolPk.toBase58(), posMint: parsed.mint.toBase58(), tokenA: '-', tokenB: '-', usd: '-' })
      continue
    }
    const pb = Buffer.from(poolAcc.data)
    // Heuristic: in CLMM pool account, token mints are at offsets ~64 and ~96; sqrtPriceX64 at ~160..176 (LE)
    const mA = new PublicKey(pb.subarray(64, 96)).toBase58()
    const mB = new PublicKey(pb.subarray(96, 128)).toBase58()
    const lo = pb.readBigUInt64LE(160), hi = pb.readBigUInt64LE(168)
    const sqrt = new Decimal(hi.toString()).times(2 ** 64).add(new Decimal(lo.toString()))
    const cur = sqrt.div(U64)

    // compute quantities at current price
    const sqrtL = sqrtFromTick(parsed.tickL)
    const sqrtU = sqrtFromTick(parsed.tickU)
    let a0 = new Decimal(0), a1 = new Decimal(0)
    if (cur.lte(sqrtL)) {
      a0 = parsed.L.times(sqrtU.minus(sqrtL)).div(sqrtL.times(sqrtU))
    } else if (cur.greaterThanOrEqualTo(sqrtU)) {
      a1 = parsed.L.times(sqrtU.minus(sqrtL))
    } else {
      a0 = sqrt.mul(1).div(sqrtU).minus(1).negated().times(parsed.L).div(sqrt) // (sqrtU - sqrtC)/(sqrtU*sqrtC) * L
      a1 = cur.minus(sqrtL).times(parsed.L)
    }

    // fetch decimals (via token program)
    const mintSet = [mA, mB]
    const mintAccs: any = await (conn as any).getMultipleAccountsInfo([new PublicKey(mA), new PublicKey(mB)], { commitment: 'confirmed' })
    const dA = mintAccs[0]?.data ? new DataView(mintAccs[0].data.buffer, mintAccs[0].data.byteOffset).getUint8(44) : 0
    const dB = mintAccs[1]?.data ? new DataView(mintAccs[1].data.buffer, mintAccs[1].data.byteOffset).getUint8(44) : 0
    const uiA = a0.div(new Decimal(10).pow(dA))
    const uiB = a1.div(new Decimal(10).pow(dB))

    let usd = new Decimal(0)
    if (fetchPrices) {
      try {
        const prices = await (fetchPrices as any).call(Price, { tokenMints: [mA, mB], connection: conn })
        const pA = new Decimal(String(prices?.[mA] || 0))
        const pB = new Decimal(String(prices?.[mB] || 0))
        usd = uiA.times(pA).add(uiB.times(pB))
      } catch { /* leave as 0 */ }
    }

    rows.push({
      poolPk: poolPk.toBase58(),
      posMint: parsed.mint.toBase58(),
      tokenA: `${uiA.toSignificantDigits(6).toString()} ${short(mA)}`,
      tokenB: `${uiB.toSignificantDigits(6).toString()} ${short(mB)}`,
      usd: `$${usd.toSignificantDigits(6).toString()}`
    })
  }

  console.log('\n💎 Raydium CL Positions (by mint, raw decode)\n')
  console.log('Pool'.padEnd(44), 'Position'.padEnd(14), 'TokenA'.padEnd(22), 'TokenB'.padEnd(22), 'USD')
  for (const r of rows) {
    console.log(
      short(r.poolPk).padEnd(12),
      short(r.posMint).padEnd(14),
      String(r.tokenA).padEnd(22),
      String(r.tokenB).padEnd(22),
      r.usd ?? '-'
    )
  }
})()
