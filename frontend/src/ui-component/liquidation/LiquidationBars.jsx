import React from 'react';
import { Box } from '@mui/material';
import LiqRow from './LiqRow';

const LiquidationBars = ({ positions }) => (
  <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 1 }}>
    {positions && positions.length
      ? positions.map((p) => (
          <LiqRow key={p.wallet_name + p.asset_type} pos={p} />
        ))
      : <p style={{ color: 'orange' }}>⚠️ No liquidation positions to display.</p>}
  </Box>
);

export default LiquidationBars;
