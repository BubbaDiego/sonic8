// @ts-nocheck
/**
 * Fetch USD prices for a list of Solana mints using Jupiter's public price API.
 * Usage:
 *   npx ts-node --transpile-only fetch_prices.ts --mints <MINT1,MINT2,...>
 */

import 'dotenv/config'
import { setTimeout as sleep } from 'timers/promises'

const argv = process.argv.slice(2)
const arg = (k: string) => { const i = argv.indexOf(k); return i >= 0 ? argv[i + 1] : undefined }

const mintsCsv = arg('--mints') || ''
const mints = mintsCsv.split(',').map(s => s.trim()).filter(Boolean)

if (!mints.length) {
  console.error('❌ No mints provided. Usage: --mints <MINT1,MINT2,...>')
  process.exit(2)
}

type JupPriceResponse = { data?: Record<string, { id?: string; price?: number; mintSymbol?: string }> }

async function fetchChunk(chunk: string[]): Promise<Record<string, number>> {
  // Jupiter v6 price endpoint accepts comma-separated ids (mints or symbols). We send mints.
  const url = `https://price.jup.ag/v6/price?ids=${encodeURIComponent(chunk.join(','))}`
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const res = await fetch(url, { method: 'GET' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = (await res.json()) as JupPriceResponse
      const out: Record<string, number> = {}
      if (json?.data) {
        for (const [k, v] of Object.entries(json.data)) {
          // Jupiter may echo back the exact mint as the key; if price is missing, skip
          if (typeof v?.price === 'number') out[k] = v.price
        }
      }
      return out
    } catch (e) {
      if (attempt === 3) throw e
      await sleep(250 * attempt) // tiny backoff
    }
  }
  return {}
}

function chunk<T>(arr: T[], size = 60): T[][] {
  const out: T[][] = []
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size))
  return out
}

(async () => {
  const uniq = Array.from(new Set(mints))
  const chunks = chunk(uniq, 60)

  const merged: Record<string, number> = {}
  for (const c of chunks) {
    const part = await fetchChunk(c)
    Object.assign(merged, part)
  }

  // Print a simple table: Mint → USD
  console.log('\n💵 Token Prices (Jupiter)\n')
  console.log('Mint'.padEnd(46), 'USD')
  for (const mint of uniq) {
    const p = merged[mint]
    const usd = (typeof p === 'number' && isFinite(p)) ? `$${p}` : '(n/a)'
    console.log(`${mint.padEnd(46)} ${usd}`)
  }

  // Exit 0 even if some are missing — still useful output
  process.exit(0)
})().catch((e) => {
  console.error('Fatal:', e?.message || e)
  process.exit(1)
})
