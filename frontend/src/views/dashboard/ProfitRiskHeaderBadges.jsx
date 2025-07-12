// material-ui
import { Stack, Typography, Avatar, Box, Tooltip } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { useEffect, useMemo } from 'react';
import { useGetPositions, refreshPositions } from 'api/positions';

function resolveWalletIcon(path, walletName) {
  if (path) {
    const cleaned = String(path).replace(/^\/+/, '');
    if (cleaned.startsWith('http')) {
      return cleaned;
    }
    if (cleaned.startsWith('static/')) {
      return '/' + cleaned;
    }
    if (!cleaned.startsWith('images/')) {
      return '/static/images/' + cleaned;
    }
    return '/static/' + cleaned;
  }

  if (walletName) {
    const icon = String(walletName)
      .replace(/\s+/g, '')
      .replace(/vault$/i, '')
      .toLowerCase();
    return `/static/images/${icon}_icon.jpg`;
  }

  return '/static/images/unknown_wallet.jpg';
}

const badgeStyle = {
  display: 'flex',
  alignItems: 'center',
  bgcolor: 'background.paper',
  borderRadius: 2,
  boxShadow: 2,
  px: 1,
  py: 0.5,
  minWidth: 120
};

export default function ProfitRiskHeaderBadges() {
  const { positions = [] } = useGetPositions();

  useEffect(() => {
    const id = setInterval(() => refreshPositions(), 60000);
    return () => clearInterval(id);
  }, []);

  const profitLeader = useMemo(() => {
    let leader = null;
    for (const p of positions) {
      const profit = parseFloat(p.pnl_after_fees_usd ?? 0);
      if (leader === null || profit > leader.profit) {
        leader = { walletIcon: resolveWalletIcon(p.wallet_image, p.wallet_name), profit };
      }
    }
    return leader;
  }, [positions]);

  const highestRisk = useMemo(() => {
    let riskiest = null;
    for (const p of positions) {
      const travel = parseFloat(p.travel_percent ?? 0);
      if (riskiest === null || travel < riskiest.travelPercent) {
        riskiest = { walletIcon: resolveWalletIcon(p.wallet_image, p.wallet_name), travelPercent: travel };
      }
    }
    return riskiest;
  }, [positions]);

  return (
    <Stack direction="row" spacing={1}>
      {profitLeader && (
        <Tooltip title="Most Profitable Position">
          <Box sx={{ ...badgeStyle, borderLeft: '4px solid', borderColor: 'success.main' }}>
            <Avatar src={profitLeader.walletIcon} sx={{ width: 24, height: 24, mr: 0.5 }} />
            <Typography variant="subtitle2" color="success.main" sx={{ fontWeight: 'bold' }}>
              ${profitLeader.profit.toFixed(2)}
            </Typography>
            <TrendingUpIcon sx={{ color: 'success.main', ml: 0.5, fontSize: 20 }} />
          </Box>
        </Tooltip>
      )}

      {highestRisk && (
        <Tooltip title="Riskiest Position">
          <Box sx={{ ...badgeStyle, borderLeft: '4px solid', borderColor: 'error.main' }}>
            <Avatar src={highestRisk.walletIcon} sx={{ width: 24, height: 24, mr: 0.5 }} />
            <Typography variant="subtitle2" color="error.main" sx={{ fontWeight: 'bold' }}>
              {highestRisk.travelPercent.toFixed(1)}%
            </Typography>
            <WarningAmberIcon sx={{ color: 'error.main', ml: 0.5, fontSize: 20 }} />
          </Box>
        </Tooltip>
      )}
    </Stack>
  );
}
