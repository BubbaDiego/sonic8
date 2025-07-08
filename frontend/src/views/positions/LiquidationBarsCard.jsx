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

      {/* Force FULL WIDTH explicitly here */}
      <Box sx={{ width: '100vw', ml: '-50vw', mr: '-50vw', position: 'relative', left: '50%', right: '50%', bgcolor: 'rgba(255,0,0,0.1)' }}>
        <LiquidationBars positions={positions} />
      </Box>
    </MainCard>
  );
};

export default LiquidationBarsCard;
