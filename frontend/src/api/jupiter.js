// frontend/src/api/jupiter.js
//
// Single place for Jupiter/Wallet API calls used by the Jupiter UI.
// All functions return parsed JSON or throw an Error with a helpful message.
//
// If you rename backend routes, update the paths here in one place.

const _json = async (url, opts = {}) => {
  const res = await fetch(url, opts);
  const text = await res.text();
  let body = {};
  try { body = text ? JSON.parse(text) : {}; } catch { /* ignore parse error */ }
  if (!res.ok) {
    // Surface a useful message
    const msg = body.detail || body.error || body.message || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return body;
};

const _get = (url) =>
  _json(url, { method: 'GET', headers: { 'Accept': 'application/json' } });

const _post = (url, data) =>
  _json(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(data ?? {})
  });

/* -------------------------------------------------------------------------- */
/* Wallet / identity                                                          */
/* -------------------------------------------------------------------------- */

// Who am I (wallet pubkey + cluster etc.)
export const whoami = () => _get('/api/jupiter/whoami');

// Human-readable signer info (method, path, derivation)
export const signerInfo = () => _get('/api/jupiter/signer/info');

// Portfolio balances for a set of mints (pass ?mints=<comma-separated> on server)
export const walletPortfolio = (mints = []) => {
  const qs = mints.length ? `?mints=${encodeURIComponent(mints.join(','))}` : '';
  return _get(`/api/jupiter/wallet/portfolio${qs}`);
};

// Estimate how much SOL is safe to spend for a swap (fees + rent buffers)
export const estimateSolSpend = ({ outMint }) =>
  _get(`/api/jupiter/wallet/estimate-sol-spend?outMint=${encodeURIComponent(outMint)}`);

/* -------------------------------------------------------------------------- */
/* Swap                                                                       */
/* -------------------------------------------------------------------------- */

// Quote a headless swap
// payload: { inMint, outMint, amountInAtoms, slippageBps, mode, restrictIntermediateTokens }
export const swapQuote = (payload) => _post('/api/jupiter/swap/quote', payload);

// Execute a previously quoted swap
// payload: whatever your backend expects (often the quote + selected route)
export const swapExecute = (payload) => _post('/api/jupiter/swap/execute', payload);

/* -------------------------------------------------------------------------- */
/* Tx log                                                                      */
/* -------------------------------------------------------------------------- */

export const txlogLatest = () => _get('/api/jupiter/txlog/latest');

export const txlogList = (limit = 25) =>
  _get(`/api/jupiter/txlog?limit=${encodeURIComponent(limit)}`);

/* -------------------------------------------------------------------------- */
/* Price helper (Jupiter price API)                                           */
/* -------------------------------------------------------------------------- */

// Fetch USD price for a mint; returns { price } or { price: null }
export async function getUsdPrice(mint, vsToken = 'USDC') {
  try {
    const u = new URL('https://price.jup.ag/v6/price');
    u.searchParams.set('ids', mint);
    u.searchParams.set('vsToken', vsToken);
    const res = await fetch(u.toString(), { method: 'GET' });
    const j = await res.json();
    const data = j?.data || {};
    // The key is usually the mint address itself; fallback to first key
    const k = data[mint] ? mint : Object.keys(data)[0];
    const price = k ? Number(data[k]?.price) : null;
    return { price: Number.isFinite(price) ? price : null };
  } catch {
    return { price: null };
  }
}

/* -------------------------------------------------------------------------- */
/* Send (SOL + SPL)                                                           */
/* -------------------------------------------------------------------------- */

// Send tokens (SOL or SPL). The backend route auto-creates the recipient ATA if needed.
// payload: { mint, to, amountAtoms }
// - mint may be 'So1111...' for SOL (or your backend can accept "SOL")
// - to is a base58 pubkey (UI normalizes; backend validates too)
export const sendToken = ({ mint, to, amountAtoms }) =>
  _post('/api/wallet/send', { mint, to, amountAtoms });

/* -------------------------------------------------------------------------- */
/* Convenience / tiny utils for consumers                                     */
/* -------------------------------------------------------------------------- */

// Helper to format numbers safely in the UI
export const fmt = (n, dp = 6) =>
  Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: dp });

// Convert atoms -> ui amount given decimals
export const atomsToUi = (atoms, decimals) =>
  Number(atoms || 0) / 10 ** Number(decimals || 0);
