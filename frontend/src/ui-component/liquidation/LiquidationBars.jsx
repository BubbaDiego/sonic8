import React from 'react';
import LiqRow from './LiqRow';

const LiquidationBars = ({ positions }) => (
  <>
    {positions && positions.length
      ? positions.map((p) => (
          <LiqRow key={p.wallet_name + p.asset_type} pos={p} />
        ))
      : <p style={{ color: 'orange' }}>⚠️ No liquidation positions to display.</p>}
  </>
);

export default LiquidationBars;
