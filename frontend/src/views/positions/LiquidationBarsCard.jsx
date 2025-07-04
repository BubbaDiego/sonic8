import React from 'react';
import MainCard from 'ui-component/cards/MainCard';
import LiquidationBars from 'ui-component/liquidation/LiquidationBars';
import { liquidationPositions } from 'data/liquidationPositions';
import { Typography, Link } from '@mui/material';

const LiquidationBarsCard = () => (
  <MainCard
    content={false}
    title={
      <span className="section-title">
        <Link href="/positions" underline="hover" onClick={() => localStorage.setItem('pc-view','liquidation')}>Liquidation Bars</Link>
        <span className="oracle-icon" data-topic="alerts" title="Ask the Oracle">🔮</span>
      </span>
    }
  >
    <div style={{ padding: '1rem' }}>
      <LiquidationBars positions={liquidationPositions} />
    </div>
  </MainCard>
);

export default LiquidationBarsCard;
