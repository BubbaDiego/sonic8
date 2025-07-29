
import React from 'react';
import { Card } from '@mui/material';
import MarketMovementCard from '../../components/MarketMovementCard';

/**
 * Simple wrapper so we have a named file‑level component. This keeps the
 * existing MarketMovementCard (which already shows 1h/6h/24h moves) while
 * aligning with the new card naming scheme requested by the user.
 */
export default function MarketMonitorCard({ cfg, setCfg, live = {}, disabled = false }) {
  return (
    <Card
      variant="outlined"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        opacity: disabled ? 0.4 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
        transition: 'opacity 0.2s ease'
      }}
    >
      <MarketMovementCard cfg={cfg} setCfg={setCfg} live={live} />
    </Card>
  );
}
