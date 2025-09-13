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

/* Triggers */
export const createSpotTrigger = (payload) => http('POST', '/api/jupiter/trigger/create', payload);
export const listSpotTriggers = (params = {}) => http('GET', '/api/jupiter/trigger/orders', null, params);
export const cancelSpotTrigger = (payload) => http('POST', '/api/jupiter/trigger/cancel', payload);

/* Swaps */
export const swapQuote   = (payload) => http('POST', '/api/jupiter/swap/quote', payload);
export const swapExecute = (payload) => http('POST', '/api/jupiter/swap/execute', payload);

/* Prices / Wallet */
export const getUsdPrice      = (id, vs = 'USDC') => http('GET', '/api/jupiter/price', null, { id, vs });
export const whoami           = () => http('GET', '/api/jupiter/whoami');
export const walletBalance    = () => http('GET', '/api/jupiter/wallet/balance');
export const estimateSolSpend = (outMint) => http('GET', '/api/jupiter/wallet/estimate-sol-spend', null, { outMint });
export const walletPortfolio  = (mintsCsv) => http('GET', '/api/jupiter/wallet/portfolio', null, mintsCsv ? { mints: mintsCsv } : undefined);

/* Txlog */
export const txlogList   = (limit=50) => http('GET', '/api/jupiter/txlog', null, { limit });
export const txlogLatest = () => http('GET', '/api/jupiter/txlog/latest');
export const txlogBySig  = (sig) => http('GET', '/api/jupiter/txlog/by-sig', null, { sig });

export default {
  createSpotTrigger, listSpotTriggers, cancelSpotTrigger,
  swapQuote, swapExecute, getUsdPrice,
  whoami, walletBalance, estimateSolSpend, walletPortfolio,
  txlogList, txlogLatest, txlogBySig
};
