import React from 'react';
import { Box, Typography, Link } from '@mui/material';
import MainCard from 'ui-component/cards/MainCard';
import LiquidationBars from 'ui-component/liquidation/LiquidationBars';
import { liquidationPositions } from 'data/liquidationPositions';

const LiquidationBarsCard = () => (
  <MainCard>
    {/* —— header identical to PositionTableCard —— */}
    <Typography variant="h4" sx={{ mb: 2 }}>
      <Link
        href="/positions"
        underline="hover"
        onClick={() => localStorage.setItem('pc-view', 'liquidation')}
      >
        Liquidation Bars
      </Link>{' '}
      <span className="oracle-icon" data-topic="alerts" title="Ask the Oracle">
        🔮
      </span>
    </Typography>

    {/* —— content —— */}
    <Box sx={{ width: '100%' }}>
      <LiquidationBars positions={liquidationPositions} />
    </Box>
  </MainCard>
);

export default LiquidationBarsCard;
