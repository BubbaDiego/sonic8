// frontend/src/api/positionsSnapshot.js
export async function fetchPositionsSnapshot(signal) {
  const res = await fetch('/api/positions/snapshot', { signal });
  if (!res.ok) throw new Error(`Snapshot fetch failed: ${res.status}`);
  return await res.json(); // { asof, rows, totals }
}
