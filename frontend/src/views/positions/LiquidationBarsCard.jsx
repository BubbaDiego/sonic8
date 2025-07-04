import React from 'react';
import { Box, Typography, Link, Paper, TableContainer } from '@mui/material';
import MainCard from 'ui-component/cards/MainCard';
import LiquidationBars from 'ui-component/liquidation/LiquidationBars';
import { useGetPositions } from 'api/positions';

const LiquidationBarsCard = () => {
  const { positions = [] } = useGetPositions();

  return (
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
      <TableContainer component={Paper} sx={{ minWidth: 320 }}>
        <Box sx={{ width: '100%', p: 1 }}>
          <LiquidationBars positions={positions} />
        </Box>
      </TableContainer>
    </MainCard>
  );
};

export default LiquidationBarsCard;
