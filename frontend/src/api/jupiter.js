// frontend/src/api/jupiter.js
// Simple fetch-based API client (no external axios client dependencies)

async function http(method, path, body, params) {
  const url = new URL(path, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    });
  }
  const res = await fetch(url.toString(), {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });

  const text = await res.text();
  let data = {};
  if (text) {
    try { data = JSON.parse(text); }
    catch { if (!res.ok) throw new Error(text || `HTTP ${res.status}`); return text; }
  }
  if (!res.ok) throw new Error(data?.detail || data?.message || `HTTP ${res.status}`);
  return data;
}

/* Triggers (kept for completeness) */
export const createSpotTrigger = (payload) => http('POST', '/api/jupiter/trigger/create', payload);
export const listSpotTriggers = (params = {}) => http('GET', '/api/jupiter/trigger/orders', null, params);
export const cancelSpotTrigger = (payload) => http('POST', '/api/jupiter/trigger/cancel', payload);

/* Swaps */
export const swapQuote   = (payload) => http('POST', '/api/jupiter/swap/quote', payload);
export const swapExecute = (payload) => http('POST', '/api/jupiter/swap/execute', payload);

/* Prices / Wallet / Portfolio */
export const getUsdPrice      = (id, vs = 'USDC') => http('GET', '/api/jupiter/price', null, { id, vs });
export const whoami           = () => http('GET', '/api/jupiter/whoami');
export const walletBalance    = () => http('GET', '/api/jupiter/wallet/balance');
export const estimateSolSpend = (outMint) => http('GET', '/api/jupiter/wallet/estimate-sol-spend', null, { outMint });
export const walletPortfolio  = (mintsCsv) => http('GET', '/api/jupiter/wallet/portfolio', null, mintsCsv ? { mints: mintsCsv } : undefined);

// send token (SOL or SPL) — backend should create recipient ATA if needed
export async function sendToken({ mint, to, amountAtoms }) {
  const r = await fetch('/api/wallet/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mint, to, amountAtoms })
  });
  const txt = await r.text();
  let j = {};
  try { j = txt ? JSON.parse(txt) : {}; } catch {}
  if (!r.ok) throw new Error(j.detail || j.error || j.message || `HTTP ${r.status}`);
  return j; // expect { signature }
}

/* Signer / Debug */
export const signerInfo  = () => http('GET', '/api/jupiter/signer/info');
export const debugSigner = () => http('GET', '/api/jupiter/debug/signer');
export const debugConfig = () => http('GET', '/api/jupiter/debug/config');

/* Txlog */
export const txlogList   = (limit = 25) => http('GET', '/api/jupiter/txlog', null, { limit });
export const txlogLatest = () => http('GET', '/api/jupiter/txlog/latest');
export const txlogBySig  = (sig) => http('GET', '/api/jupiter/txlog/by-sig', null, { sig });

export default {
  createSpotTrigger, listSpotTriggers, cancelSpotTrigger,
  swapQuote, swapExecute, getUsdPrice,
  whoami, walletBalance, estimateSolSpend, walletPortfolio, sendToken,
  signerInfo, debugSigner, debugConfig,
  txlogList, txlogLatest, txlogBySig
};
