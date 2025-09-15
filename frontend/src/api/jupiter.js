// frontend/src/api/jupiter.js
// Consolidated API used by the Jupiter UI.

const _json = async (url, opts = {}) => {
  const res = await fetch(url, opts);
  const text = await res.text();
  let body = {};
  try { body = text ? JSON.parse(text) : {}; } catch {}
  if (!res.ok) throw new Error(body.detail || body.error || body.message || `HTTP ${res.status}`);
  return body;
};

const _get  = (url)   => _json(url, { method: 'GET',  headers: { 'Accept':'application/json' } });
const _post = (url,d)=> _json(url, { method: 'POST', headers: { 'Content-Type':'application/json','Accept':'application/json' }, body: JSON.stringify(d||{}) });

// Identity / wallet
export const whoami          = () => _get('/api/jupiter/whoami');
export const signerInfo      = () => _get('/api/jupiter/signer/info');
export const walletPortfolio = (mints=[]) => {
  const qs = mints.length ? `?mints=${encodeURIComponent(mints.join(','))}` : '';
  return _get(`/api/jupiter/wallet/portfolio${qs}`);
};
export const estimateSolSpend = ({ outMint }) =>
  _get(`/api/jupiter/wallet/estimate-sol-spend?outMint=${encodeURIComponent(outMint)}`);

// Swap
export const swapQuote   = (payload) => _post('/api/jupiter/swap/quote', payload);
export const swapExecute = (payload) => _post('/api/jupiter/swap/execute', payload);

// Tx log
export const txlogLatest = () => _get('/api/jupiter/txlog/latest');
export const txlogList   = (limit=25) => _get(`/api/jupiter/txlog?limit=${encodeURIComponent(limit)}`);

// Price helper
export async function getUsdPrice(mint, vsToken='USDC'){
  try{
    const u=new URL('https://price.jup.ag/v6/price');
    u.searchParams.set('ids',mint); u.searchParams.set('vsToken',vsToken);
    const j=await (await fetch(u.toString(),{method:'GET'})).json();
    const d=j?.data||{}; const k=d[mint]?mint:Object.keys(d)[0];
    const p=k?Number(d[k]?.price):null; return { price:Number.isFinite(p)?p:null };
  }catch{ return { price:null }; }
}

// Send (SOL + SPL)
export const sendToken = ({ mint, to, amountAtoms }) =>
  _post('/api/wallet/send', { mint, to, amountAtoms });

// Convenience
export const fmt       = (n,dp=6)=>Number(n||0).toLocaleString(undefined,{maximumFractionDigits:dp});
export const atomsToUi = (a,d)=>Number(a||0)/10**Number(d||0);

export const preflightSend = ({ mint, to, amountAtoms }) =>
  _post('/api/wallet/preflight-send', { mint, to, amountAtoms });
