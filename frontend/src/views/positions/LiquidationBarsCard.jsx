import React from 'react';
import { Box, Typography } from '@mui/material';
import MainCard from 'ui-component/cards/MainCard';
import LiquidationBars from 'ui-component/liquidation/LiquidationBars';
import { useGetPositions } from 'api/positions';

const LiquidationBarsCard = () => {
  const { positions = [] } = useGetPositions();

  return (
    <MainCard>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Liquidation Bars 🔮
      </Typography>

      {/* Corrected and normal width (no debug overrides!) */}
      <Box sx={{ width: '100%' }}>
        <LiquidationBars positions={positions} />
      </Box>
    </MainCard>
  );
};

export default LiquidationBarsCard;
