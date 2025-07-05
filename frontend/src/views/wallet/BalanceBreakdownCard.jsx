import React, { useMemo } from 'react';
import MainCard from 'ui-component/cards/MainCard';
import WalletPieCard from 'ui-component/wallet/WalletPieCard';
import { Typography } from '@mui/material';

export default function BalanceBreakdownCard({ wallets = [] }) {
  const data = useMemo(() => {
    if (!wallets.length) return null;
    const total = wallets.reduce((sum, w) => sum + (parseFloat(w.balance) || 0), 0);
    if (!total) return null;
    const labels = wallets.map((w) => w.name);
    const series = wallets.map((w) => Number(((parseFloat(w.balance) || 0) / total * 100).toFixed(2)));
    return { labels, series, colors: {} };
  }, [wallets]);

  return (
    <MainCard>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Balance Breakdown
      </Typography>
      {data && <WalletPieCard data={data} />}
    </MainCard>
  );
}
