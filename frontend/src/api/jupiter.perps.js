// frontend/src/api/jupiter.perps.js
async function http(method, path, body, params) {
  const url = new URL(path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => v != null && url.searchParams.set(k, String(v)));
  const res = await fetch(url.toString(), {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  const text = await res.text();
  let data = {};
  if (text) { try { data = JSON.parse(text); } catch { if (!res.ok) throw new Error(text); return text; } }
  if (!res.ok) throw new Error(data?.detail || data?.message || `HTTP ${res.status}`);
  return data;
}

export const perpsMarkets   = () => http('GET', '/api/perps/markets');
export const perpsPositions = (owner) => http('GET', '/api/perps/positions', null, owner ? { owner } : undefined);
export const createPerpOrder = (body) => http('POST', '/api/perps/order', body);
export const closePerpPosition = (body) => http('POST', '/api/perps/close', body);

export default { perpsMarkets, perpsPositions, createPerpOrder, closePerpPosition };
