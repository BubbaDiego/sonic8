import React from 'react';
import { Box, Typography } from '@mui/material';
import FullWidthPaper from 'ui-component/cards/FullWidthPaper';
import MainCard from 'ui-component/cards/MainCard';
import LiquidationBars from 'ui-component/liquidation/LiquidationBars';
import { useGetPositions } from 'api/positions';

const LiquidationBarsCard = () => {
  const { positions = [] } = useGetPositions();

  return (
    <MainCard>
      {/* Header now matches PositionTableCard: plain text, no navigation */}
      <Typography variant="h4" sx={{ mb: 2 }}>
        Liquidation Bars{' '}
        <span className="oracle-icon" data-topic="alerts" title="Ask the Oracle">
          🔮
        </span>
      </Typography>

      {/* —— content —— */}
      {/* Full-width Paper so card matches table card footprint */}
      <FullWidthPaper>
        <Box sx={{ width: '100%', p: 1 }}>
          <LiquidationBars positions={positions} />
        </Box>
      </FullWidthPaper>
    </MainCard>
  );
};

export default LiquidationBarsCard;
