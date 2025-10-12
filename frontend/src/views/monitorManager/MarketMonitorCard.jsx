import React from 'react';
import { Card } from '@mui/material';
import MarketMovementCard from 'components/MarketMovementCard';

/**
 * Thin wrapper that provides disabled overlay styling consistent with other cards.
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
      <MarketMovementCard cfg={cfg} setCfg={setCfg} live={live} disabled={disabled} />
    </Card>
  );
}

