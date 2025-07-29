
import React from 'react';
import MarketMovementCard from '../../components/MarketMovementCard';

/**
 * Simple wrapper so we have a named file‑level component. This keeps the
 * existing MarketMovementCard (which already shows 1h/6h/24h moves) while
 * aligning with the new card naming scheme requested by the user.
 */
export default function MarketMonitorCard({ cfg, setCfg, live }) {
  return <MarketMovementCard cfg={cfg} setCfg={setCfg} live={live} />;
}
