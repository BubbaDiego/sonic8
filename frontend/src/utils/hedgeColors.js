// deterministic colour picker for hedge groups
const PALETTE = [
  '#3b82f6', // blue-500
  '#f59e0b', // amber-500
  '#10b981', // emerald-500
  '#f43f5e', // rose-500
  '#8b5cf6', // violet-500
  '#14b8a6', // teal-500
];

const cache = new Map();

/**
 * @param {string|null|undefined} hedgeId
 * @returns {string} CSS colour; 'transparent' if no hedge
 */
export default function colorForHedge(hedgeId) {
  if (!hedgeId) return 'transparent';
  if (!cache.has(hedgeId)) {
    cache.set(hedgeId, PALETTE[cache.size % PALETTE.length]);
  }
  return cache.get(hedgeId);
}
